"""
后台 Worker 进程

异步执行时，通过 subprocess.Popen 启动独立子进程，
子进程通过 WebSocket 监听 kernel 执行完成，
完成后将 output/error 写入 .task_state.json。

直接运行：
    python worker.py <task_id> <kernel_id> <timeout> <server_id>
"""

import json
import os
import re
import sys
import time
import uuid
import websocket

# 将 jupyter_tools 目录加入路径（子进程直接运行时需要）
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from task import finish_task, get_log_path
from config import get_server_config
from notifier import send_task_notification

_TASK_LOGS_DIR = os.path.join(_TOOLS_DIR, "..", ".task_logs")


def run(task_id: str, kernel_id: str, timeout: int, server_id: str):
    """执行代码，完成后更新任务状态（在独立进程中运行）"""
    os.makedirs(_TASK_LOGS_DIR, exist_ok=True)
    log_path = get_log_path(task_id)

    # 从 .task_state.json 读取代码
    state_file = os.path.join(_TOOLS_DIR, "..", ".task_state.json")
    try:
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
        # code 存储在 _code 字段（由 submit_async 写入）
        code = state.get(task_id, {}).get("_code", "")
    except Exception as e:
        finish_task(task_id, output="", error=f"[读取任务代码失败] {e}")
        return

    if not code:
        finish_task(task_id, output="", error="[任务代码为空]")
        return

    try:
        cfg = get_server_config(server_id or None)
        ws = websocket.create_connection(
            f"{cfg['WS_URL']}/api/kernels/{kernel_id}/channels",
            header=[f"Authorization: token {cfg['TOKEN']}"],
            timeout=timeout
        )
    except Exception as e:
        finish_task(task_id, output="", error=f"[连接失败] {e}")
        return

    msg_id = str(uuid.uuid4())
    execute_msg = {
        "header": {
            "msg_id": msg_id,
            "msg_type": "execute_request",
            "username": "claude",
            "session": str(uuid.uuid4()),
            "version": "5.3"
        },
        "parent_header": {},
        "metadata": {},
        "content": {
            "code": code,
            "silent": False,
            "store_history": True,
            "user_expressions": {},
            "allow_stdin": False
        }
    }

    ws.send(json.dumps(execute_msg))

    outputs = []
    errors = []
    deadline = time.time() + timeout

    with open(log_path, "a", encoding="utf-8", buffering=1) as log_file:
        try:
            while time.time() < deadline:
                try:
                    ws.settimeout(deadline - time.time())
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    errors.append(f"[超时] 执行超过 {timeout} 秒")
                    break

                msg = json.loads(raw)
                msg_type = msg.get("header", {}).get("msg_type", "")
                parent_id = msg.get("parent_header", {}).get("msg_id", "")

                if parent_id != msg_id:
                    continue

                if msg_type == "stream":
                    text = msg["content"]["text"]
                    outputs.append(text)
                    log_file.write(text)

                elif msg_type == "execute_result":
                    text = msg["content"]["data"].get("text/plain", "")
                    outputs.append(text)
                    log_file.write(text + "\n")

                elif msg_type == "display_data":
                    data = msg["content"]["data"]
                    if "text/plain" in data:
                        text = data["text/plain"]
                        outputs.append(text)
                        log_file.write(text + "\n")

                elif msg_type == "error":
                    tb = msg["content"]["traceback"]
                    clean_tb = [re.sub(r'\x1b\[[0-9;]*m', '', line) for line in tb]
                    err_text = "\n".join(clean_tb)
                    errors.append(err_text)
                    log_file.write("[ERROR]\n" + err_text + "\n")

                elif msg_type == "status":
                    if msg["content"]["execution_state"] == "idle":
                        break
        finally:
            ws.close()

    final_output = "".join(outputs)
    final_error = "\n".join(errors)
    finish_task(task_id, output=final_output, error=final_error)
    send_task_notification(task_id, final_output, final_error)


def submit_async(task_id: str, kernel_id: str, code: str, timeout: int = 3600,
                 server_id: str = None):
    """
    将代码写入任务状态，启动独立子进程执行，立即返回。
    子进程独立于 CLI 进程，CLI 退出后继续运行。
    """
    import subprocess

    # 将完整代码存入 _code 字段供子进程读取
    state_file = os.path.join(_TOOLS_DIR, "..", ".task_state.json")
    try:
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}
    if task_id in state:
        state[task_id]["_code"] = code
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    worker_script = os.path.abspath(__file__)
    proc = subprocess.Popen(
        [sys.executable, worker_script,
         task_id, kernel_id, str(timeout), server_id or ""],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True   # 脱离父进程组，CLI 退出后继续运行
    )
    return proc


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python worker.py <task_id> <kernel_id> <timeout> <server_id>")
        sys.exit(1)

    _task_id = sys.argv[1]
    _kernel_id = sys.argv[2]
    _timeout = int(sys.argv[3])
    _server_id = sys.argv[4] or None

    run(_task_id, _kernel_id, _timeout, _server_id)
