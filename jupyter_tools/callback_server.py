"""
本地 HTTP 回调服务

在本机启动轻量 HTTP Server，监听来自 Jupyter 服务器的任务完成通知。
异步任务执行时，在代码末尾自动注入回调请求，任务完成后主动通知本机。

端口：18888（可通过 JUPYTER_CALLBACK_PORT 环境变量覆盖）
接口：POST /callback  Body: {"task_id": "...", "status": "done"|"error", "message": "..."}
"""

import json
import os
import signal
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from task import finish_task

CALLBACK_PORT = int(os.environ.get("JUPYTER_CALLBACK_PORT", 18888))
_PID_FILE = os.path.join(os.path.dirname(__file__), "..", ".callback_server.pid")


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        task_id = data.get("task_id", "")
        status = data.get("status", "done")
        message = data.get("message", "")

        if task_id:
            if status == "error":
                finish_task(task_id, output="", error=message or "[远程回调: 执行失败]")
            else:
                finish_task(task_id, output=message or "[远程回调: 执行完成]", error="")
            print(f"[📩 回调收到] task_id={task_id} status={status}", flush=True)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, format, *args):
        # 抑制默认的 access log，只保留回调日志
        pass


def _write_pid():
    with open(_PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def _remove_pid():
    if os.path.exists(_PID_FILE):
        os.remove(_PID_FILE)


def read_pid() -> int | None:
    if not os.path.exists(_PID_FILE):
        return None
    with open(_PID_FILE) as f:
        try:
            return int(f.read().strip())
        except ValueError:
            return None


def is_running() -> bool:
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        _remove_pid()
        return False


def start_server():
    """启动 Callback Server（前台运行，调用方负责后台化）"""
    _write_pid()

    def _handle_signal(sig, frame):
        _remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    server = HTTPServer(("0.0.0.0", CALLBACK_PORT), _CallbackHandler)
    print(f"[🌐 Callback Server 已启动] 监听 0.0.0.0:{CALLBACK_PORT}", flush=True)
    try:
        server.serve_forever()
    finally:
        _remove_pid()


def stop_server():
    """停止 Callback Server"""
    pid = read_pid()
    if pid is None:
        print("（Callback Server 未运行）")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        _remove_pid()
        print(f"[🛑 Callback Server 已停止] PID={pid}")
    except ProcessLookupError:
        _remove_pid()
        print(f"（进程 {pid} 已不存在，已清理 PID 文件）")


def build_callback_snippet(task_id: str, port: int = CALLBACK_PORT) -> str:
    """
    生成注入到用户代码末尾的回调片段。
    使用标准库 urllib，避免依赖 requests。
    """
    return f"""
# ── [自动注入] 任务完成回调，请勿修改 ──
import urllib.request as _cb_urllib, json as _cb_json
try:
    _cb_data = _cb_json.dumps({{"task_id": "{task_id}", "status": "done"}}).encode()
    _cb_req = _cb_urllib.Request(
        "http://localhost:{port}/callback",
        data=_cb_data,
        headers={{"Content-Type": "application/json"}},
        method="POST"
    )
    _cb_urllib.urlopen(_cb_req, timeout=5)
except Exception:
    pass
# ── [自动注入结束] ──
"""


if __name__ == "__main__":
    start_server()
