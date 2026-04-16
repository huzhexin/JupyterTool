"""
任务状态管理模块

负责读写 .task_state.json，以及查看任务日志。

状态字段：
    status: "running" | "done" | "error"
    submit_time: ISO 时间字符串
    kernel_id: str
    server_id: str
    code_snippet: 代码前 80 字符
    output: 执行输出（完成后填入）
    error: 错误信息（失败后填入）
    finish_time: ISO 时间字符串（完成后填入）
"""

import json
import os
from datetime import datetime

_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", ".task_state.json")
_TASK_LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", ".task_logs")


# ── 状态读写 ──────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def create_task(task_id: str, kernel_id: str, server_id: str, code: str):
    """注册一个新任务（状态为 running）"""
    state = _load_state()
    state[task_id] = {
        "status": "running",
        "submit_time": datetime.now().isoformat(timespec="seconds"),
        "kernel_id": kernel_id,
        "server_id": server_id or "",
        "code_snippet": code[:80].replace("\n", " "),
        "output": "",
        "error": "",
        "finish_time": "",
    }
    _save_state(state)


def finish_task(task_id: str, output: str, error: str):
    """标记任务完成，写入输出结果"""
    state = _load_state()
    if task_id not in state:
        return
    state[task_id]["status"] = "done" if not error else "error"
    state[task_id]["output"] = output
    state[task_id]["error"] = error
    state[task_id]["finish_time"] = datetime.now().isoformat(timespec="seconds")
    _save_state(state)


def get_task(task_id: str) -> dict | None:
    """获取单个任务信息"""
    return _load_state().get(task_id)


def list_tasks() -> list[dict]:
    """返回所有任务列表（按提交时间倒序）"""
    state = _load_state()
    tasks = [{"task_id": tid, **info} for tid, info in state.items()]
    tasks.sort(key=lambda t: t.get("submit_time", ""), reverse=True)
    return tasks


def clean_tasks():
    """清除所有已完成/失败的任务记录（保留 running）"""
    state = _load_state()
    cleaned = {tid: info for tid, info in state.items() if info["status"] == "running"}
    removed = len(state) - len(cleaned)
    _save_state(cleaned)
    return removed


# ── 日志操作 ──────────────────────────────────────────────────────────────────

def get_log_path(task_id: str) -> str:
    return os.path.join(_TASK_LOGS_DIR, f"{task_id}.log")


def read_task_logs(task_id: str, tail: int = None) -> str:
    """读取任务日志，tail 指定最后 N 行（None 表示全部）"""
    log_path = get_log_path(task_id)
    if not os.path.exists(log_path):
        return ""
    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    if tail is not None:
        lines = lines[-tail:]
    return "".join(lines)


# ── 打印辅助 ──────────────────────────────────────────────────────────────────

def print_task(task_id: str, info: dict):
    status_icon = {"running": "🔄", "done": "✅", "error": "❌"}.get(info["status"], "?")
    print(f"  {status_icon} [{task_id}]")
    print(f"     状态: {info['status']}  提交: {info['submit_time']}", end="")
    if info.get("finish_time"):
        print(f"  完成: {info['finish_time']}", end="")
    print()
    print(f"     服务器: {info['server_id'] or '默认'}  Kernel: {info['kernel_id']}")
    print(f"     代码: {info['code_snippet']}")
