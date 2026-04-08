import json
import os
import requests
from config import get_server_config

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", ".kernel_state.json")


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def save_kernel_id(kernel_id: str, server_id: str = None):
    """持久化保存指定服务器的 kernel ID"""
    cfg = get_server_config(server_id)
    state = _load_state()
    state[cfg["id"]] = kernel_id
    _save_state(state)


def load_kernel_id(server_id: str = None) -> str | None:
    """读取指定服务器上次保存的 kernel ID"""
    cfg = get_server_config(server_id)
    return _load_state().get(cfg["id"])


def clear_kernel_id(server_id: str = None):
    """清除指定服务器保存的 kernel ID"""
    cfg = get_server_config(server_id)
    state = _load_state()
    state.pop(cfg["id"], None)
    _save_state(state)


def create_kernel(kernel_name="python3", server_id: str = None) -> str:
    """创建新 Kernel，返回 kernel_id"""
    cfg = get_server_config(server_id)
    resp = requests.post(
        f"{cfg['BASE_URL']}/api/kernels",
        headers=cfg["HEADERS"],
        json={"name": kernel_name}
    )
    resp.raise_for_status()
    kernel_id = resp.json()["id"]
    print(f"[✅ Kernel 已创建] {kernel_id}  ({cfg['name']})")
    return kernel_id


def list_kernels(server_id: str = None) -> list:
    """列出所有运行中的 Kernel"""
    cfg = get_server_config(server_id)
    resp = requests.get(f"{cfg['BASE_URL']}/api/kernels", headers=cfg["HEADERS"])
    resp.raise_for_status()
    kernels = resp.json()
    print(f"[服务器: {cfg['name']} ({cfg['id']})]")
    for k in kernels:
        print(f"  - {k['id']} | {k['name']} | {k['execution_state']}")
    return kernels


def get_kernel(kernel_id: str, server_id: str = None) -> dict:
    """获取指定 Kernel 信息"""
    cfg = get_server_config(server_id)
    resp = requests.get(f"{cfg['BASE_URL']}/api/kernels/{kernel_id}", headers=cfg["HEADERS"])
    resp.raise_for_status()
    return resp.json()


def restart_kernel(kernel_id: str, server_id: str = None):
    """重启 Kernel（清空所有变量）"""
    cfg = get_server_config(server_id)
    resp = requests.post(
        f"{cfg['BASE_URL']}/api/kernels/{kernel_id}/restart",
        headers=cfg["HEADERS"]
    )
    resp.raise_for_status()
    print(f"[🔄 Kernel 已重启] {kernel_id}")


def interrupt_kernel(kernel_id: str, server_id: str = None):
    """中断 Kernel 当前执行"""
    cfg = get_server_config(server_id)
    resp = requests.post(
        f"{cfg['BASE_URL']}/api/kernels/{kernel_id}/interrupt",
        headers=cfg["HEADERS"]
    )
    resp.raise_for_status()
    print(f"[⏹ Kernel 已中断] {kernel_id}")


def delete_kernel(kernel_id: str, server_id: str = None):
    """删除 Kernel"""
    cfg = get_server_config(server_id)
    requests.delete(f"{cfg['BASE_URL']}/api/kernels/{kernel_id}", headers=cfg["HEADERS"])
    print(f"[🗑 Kernel 已删除] {kernel_id}")


def get_or_create_kernel(kernel_id: str = None, server_id: str = None) -> str:
    """
    优先级：传入的 kernel_id > 本地保存的 kernel_id > 新建
    自动将最终使用的 kernel_id 持久化到 .kernel_state.json（按服务器隔离）
    """
    if not kernel_id:
        kernel_id = load_kernel_id(server_id)
        if kernel_id:
            print(f"[📂 读取已保存 Kernel] {kernel_id}")

    if kernel_id:
        try:
            k = get_kernel(kernel_id, server_id)
            print(f"[♻️ 复用 Kernel] {k['id']} | 状态: {k['execution_state']}")
            save_kernel_id(kernel_id, server_id)
            return kernel_id
        except Exception:
            print("[⚠️ Kernel 不存在，重新创建]")

    kid = create_kernel(server_id=server_id)
    save_kernel_id(kid, server_id)
    return kid
