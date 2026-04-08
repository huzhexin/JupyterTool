import json
import requests
from config import get_server_config
from permissions import check_path_allowed, check_delete_allowed, check_write_allowed


def list_notebooks(path: str = "", server_id: str = None) -> list:
    """列出指定目录下的所有 notebook"""
    cfg = get_server_config(server_id)
    resp = requests.get(
        f"{cfg['BASE_URL']}/api/contents/{path}",
        headers=cfg["HEADERS"]
    )
    resp.raise_for_status()
    items = resp.json().get("content", [])
    notebooks = [i for i in items if i["type"] == "notebook"]
    for nb in notebooks:
        print(f"  - {nb['path']}")
    return notebooks


def list_directory(path: str = "", server_id: str = None) -> list:
    """列出目录内容（文件和子目录）"""
    if path:
        check_path_allowed(path)
    cfg = get_server_config(server_id)
    resp = requests.get(
        f"{cfg['BASE_URL']}/api/contents/{path}",
        headers=cfg["HEADERS"]
    )
    resp.raise_for_status()
    items = resp.json().get("content", [])
    for item in items:
        print(f"  [{item['type']}] {item['path']}")
    return items


def read_notebook(path: str, server_id: str = None) -> dict:
    """读取 notebook 内容，返回完整 nbformat"""
    cfg = get_server_config(server_id)
    resp = requests.get(
        f"{cfg['BASE_URL']}/api/contents/{path}",
        headers=cfg["HEADERS"]
    )
    resp.raise_for_status()
    return resp.json()["content"]


def save_notebook(path: str, notebook: dict, server_id: str = None):
    """保存 notebook 到服务器"""
    check_write_allowed(path)
    cfg = get_server_config(server_id)
    resp = requests.put(
        f"{cfg['BASE_URL']}/api/contents/{path}",
        headers=cfg["HEADERS"],
        json={"type": "notebook", "content": notebook}
    )
    resp.raise_for_status()
    print(f"[💾 Notebook 已保存] {path}")


def create_notebook(path: str, cells: list = None, server_id: str = None):
    """
    创建新 notebook
    cells: [{"type": "code"/"markdown", "source": "..."}]
    """
    check_write_allowed(path)
    nb_cells = []
    for cell in (cells or []):
        nb_cells.append({
            "cell_type": cell.get("type", "code"),
            "source": cell.get("source", ""),
            "metadata": {},
            "outputs": [],
            "execution_count": None
        })

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            }
        },
        "cells": nb_cells
    }

    cfg = get_server_config(server_id)
    resp = requests.put(
        f"{cfg['BASE_URL']}/api/contents/{path}",
        headers=cfg["HEADERS"],
        json={"type": "notebook", "content": notebook}
    )
    resp.raise_for_status()
    print(f"[📓 Notebook 已创建] {path}")
    return notebook


def append_cell(path: str, code: str, cell_type: str = "code", server_id: str = None):
    """向已有 notebook 追加一个 cell"""
    nb = read_notebook(path, server_id)
    nb["cells"].append({
        "cell_type": cell_type,
        "source": code,
        "metadata": {},
        "outputs": [],
        "execution_count": None
    })
    save_notebook(path, nb, server_id)
    print(f"[➕ Cell 已追加] {path}")


def update_cell_output(path: str, cell_index: int, outputs: list, server_id: str = None):
    """更新指定 cell 的输出结果"""
    nb = read_notebook(path, server_id)
    nb["cells"][cell_index]["outputs"] = outputs
    save_notebook(path, nb, server_id)


def get_all_code(path: str, server_id: str = None) -> str:
    """提取 notebook 中所有 code cell 的代码"""
    nb = read_notebook(path, server_id)
    codes = []
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            codes.append(cell["source"])
    return "\n\n# --- next cell ---\n\n".join(codes)


def delete_notebook(path: str, server_id: str = None):
    """删除 notebook"""
    check_delete_allowed(path)
    cfg = get_server_config(server_id)
    requests.delete(f"{cfg['BASE_URL']}/api/contents/{path}", headers=cfg["HEADERS"])
    print(f"[🗑 Notebook 已删除] {path}")


def write_file(path: str, content: str, server_id: str = None):
    """在 Jupyter 服务器上写入/创建文本文件"""
    check_write_allowed(path)
    cfg = get_server_config(server_id)
    resp = requests.put(
        f"{cfg['BASE_URL']}/api/contents/{path}",
        headers=cfg["HEADERS"],
        json={"type": "file", "format": "text", "content": content}
    )
    resp.raise_for_status()
    print(f"[📝 文件已写入] {path}")


def read_file(path: str, server_id: str = None) -> str:
    """读取 Jupyter 服务器上的文本文件"""
    cfg = get_server_config(server_id)
    resp = requests.get(
        f"{cfg['BASE_URL']}/api/contents/{path}",
        headers=cfg["HEADERS"]
    )
    resp.raise_for_status()
    return resp.json()["content"]


def delete_file(path: str, server_id: str = None):
    """删除 Jupyter 服务器上的文件"""
    check_delete_allowed(path)
    cfg = get_server_config(server_id)
    requests.delete(f"{cfg['BASE_URL']}/api/contents/{path}", headers=cfg["HEADERS"])
    print(f"[🗑 文件已删除] {path}")
