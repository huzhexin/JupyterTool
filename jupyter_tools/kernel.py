import json
import os
import requests
from config import BASE_URL, HEADERS

STATE_FILE = os.path.join(os.path.dirname(__file__), ".kernel_state.json")


def save_kernel_id(kernel_id: str):
    """持久化保存当前 kernel ID"""
    with open(STATE_FILE, "w") as f:
        json.dump({"kernel_id": kernel_id}, f)


def load_kernel_id() -> str | None:
    """读取上次保存的 kernel ID"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f).get("kernel_id")
    return None


def clear_kernel_id():
    """清除保存的 kernel ID"""
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def create_kernel(kernel_name="python3") -> str:
    """创建新 Kernel，返回 kernel_id"""
    resp = requests.post(
        f"{BASE_URL}/api/kernels",
        headers=HEADERS,
        json={"name": kernel_name}
    )
    resp.raise_for_status()
    kernel_id = resp.json()["id"]
    print(f"[✅ Kernel 已创建] {kernel_id}")
    return kernel_id


def list_kernels() -> list:
    """列出所有运行中的 Kernel"""
    resp = requests.get(f"{BASE_URL}/api/kernels", headers=HEADERS)
    resp.raise_for_status()
    kernels = resp.json()
    for k in kernels:
        print(f"  - {k['id']} | {k['name']} | {k['execution_state']}")
    return kernels


def get_kernel(kernel_id: str) -> dict:
    """获取指定 Kernel 信息"""
    resp = requests.get(f"{BASE_URL}/api/kernels/{kernel_id}", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def restart_kernel(kernel_id: str):
    """重启 Kernel（清空所有变量）"""
    resp = requests.post(
        f"{BASE_URL}/api/kernels/{kernel_id}/restart",
        headers=HEADERS
    )
    resp.raise_for_status()
    print(f"[🔄 Kernel 已重启] {kernel_id}")


def interrupt_kernel(kernel_id: str):
    """中断 Kernel 当前执行"""
    resp = requests.post(
        f"{BASE_URL}/api/kernels/{kernel_id}/interrupt",
        headers=HEADERS
    )
    resp.raise_for_status()
    print(f"[⏹ Kernel 已中断] {kernel_id}")


def delete_kernel(kernel_id: str):
    """删除 Kernel"""
    requests.delete(f"{BASE_URL}/api/kernels/{kernel_id}", headers=HEADERS)
    print(f"[🗑 Kernel 已删除] {kernel_id}")


def get_or_create_kernel(kernel_id: str = None) -> str:
    """
    优先级：传入的 kernel_id > 本地保存的 kernel_id > 新建
    自动将最终使用的 kernel_id 持久化到 .kernel_state.json
    """
    # 没传入则尝试读本地保存的
    if not kernel_id:
        kernel_id = load_kernel_id()
        if kernel_id:
            print(f"[📂 读取已保存 Kernel] {kernel_id}")

    if kernel_id:
        try:
            k = get_kernel(kernel_id)
            print(f"[♻️ 复用 Kernel] {k['id']} | 状态: {k['execution_state']}")
            save_kernel_id(kernel_id)
            return kernel_id
        except Exception:
            print("[⚠️ Kernel 不存在，重新创建]")

    kid = create_kernel()
    save_kernel_id(kid)
    return kid
