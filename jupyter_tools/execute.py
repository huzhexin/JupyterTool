import json
import re
import time
import uuid
import websocket
from config import get_server_config


def execute_code(kernel_id: str, code: str, timeout: int = 60, server_id: str = None) -> dict:
    """
    在指定 Kernel 中执行代码

    返回:
        {
            "success": bool,
            "output": str,
            "error": str,
            "displays": list,
        }
    """
    cfg = get_server_config(server_id)
    ws = websocket.create_connection(
        f"{cfg['WS_URL']}/api/kernels/{kernel_id}/channels",
        header=[f"Authorization: token {cfg['TOKEN']}"],
        timeout=timeout
    )

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
    displays = []
    deadline = time.time() + timeout

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
            outputs.append(msg["content"]["text"])

        elif msg_type == "execute_result":
            outputs.append(msg["content"]["data"].get("text/plain", ""))

        elif msg_type == "display_data":
            data = msg["content"]["data"]
            if "image/png" in data:
                displays.append({"type": "image", "data": data["image/png"]})
            elif "text/html" in data:
                displays.append({"type": "html", "data": data["text/html"]})
            elif "text/plain" in data:
                outputs.append(data["text/plain"])

        elif msg_type == "error":
            tb = msg["content"]["traceback"]
            clean_tb = [re.sub(r'\x1b\[[0-9;]*m', '', line) for line in tb]
            errors.append("\n".join(clean_tb))

        elif msg_type == "status":
            if msg["content"]["execution_state"] == "idle":
                break

    ws.close()

    return {
        "success": len(errors) == 0,
        "output": "".join(outputs),
        "error": "\n".join(errors),
        "displays": displays
    }


def execute_file(kernel_id: str, filepath: str, timeout: int = 60, server_id: str = None) -> dict:
    """读取 .py 文件内容并执行"""
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    print(f"[📄 执行文件] {filepath}")
    return execute_code(kernel_id, code, timeout, server_id)


def execute_cells(kernel_id: str, cells: list, stop_on_error: bool = True, server_id: str = None) -> list:
    """按顺序执行多个代码块"""
    results = []
    for i, cell in enumerate(cells):
        print(f"\n[▶ 执行 Cell {i+1}/{len(cells)}]")
        result = execute_code(kernel_id, cell, server_id=server_id)
        result["cell_index"] = i
        result["code"] = cell
        results.append(result)

        if not result["success"] and stop_on_error:
            print(f"[❌ Cell {i+1} 失败，停止执行]")
            break

    return results
