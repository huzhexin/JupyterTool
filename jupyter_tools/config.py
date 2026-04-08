"""
多服务器配置模块

config.ini 格式：
    [servers]
    default = server1

    [server1]
    host  = 33.32.31.46
    port  = 8420
    token = xxx
    name  = 训练机A       # 可选，显示名称

用法：
    cfg = get_server_config()            # 使用默认服务器
    cfg = get_server_config("server2")   # 指定服务器
    servers = list_servers()             # 列出所有服务器
"""

import configparser
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.ini")
_SESSION_FILE = os.path.join(os.path.dirname(__file__), "..", ".session_servers")


def _load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(_CONFIG_PATH)
    return cfg


def list_servers() -> list[dict]:
    """返回所有已配置的服务器列表"""
    cfg = _load_cfg()
    default = cfg.get("servers", "default", fallback=None)
    result = []
    for section in cfg.sections():
        if section in ("servers", "permissions"):
            continue
        entry = {
            "id": section,
            "host": cfg.get(section, "host", fallback=""),
            "port": cfg.get(section, "port", fallback=""),
            "name": cfg.get(section, "name", fallback=section),
            "is_default": (section == default),
        }
        result.append(entry)
    return result


def get_default_server_id() -> str | None:
    """返回默认服务器 ID"""
    cfg = _load_cfg()
    default = cfg.get("servers", "default", fallback=None)
    if default:
        return default
    # 没有 [servers] default，取第一个非 servers/permissions section
    for section in cfg.sections():
        if section not in ("servers", "permissions"):
            return section
    return None


def get_session_servers() -> list[str] | None:
    """
    读取 .session_servers 文件，返回本 session 允许的服务器 ID 列表。
    文件不存在则返回 None（表示不限制）。
    """
    if not os.path.exists(_SESSION_FILE):
        return None
    with open(_SESSION_FILE) as f:
        ids = [line.strip() for line in f if line.strip()]
    return ids if ids else None


def set_session_servers(server_ids: list[str]):
    """设置本 session 允许的服务器列表"""
    with open(_SESSION_FILE, "w") as f:
        f.write("\n".join(server_ids) + "\n")


def clear_session_servers():
    """清除 session 限制"""
    if os.path.exists(_SESSION_FILE):
        os.remove(_SESSION_FILE)


def get_server_config(server_id: str = None) -> dict:
    """
    获取指定服务器的连接配置。

    返回：
        {
            "id":       服务器 ID（如 "server1"）,
            "name":     显示名称,
            "BASE_URL": "http://host:port",
            "TOKEN":    "xxx",
            "HEADERS":  {"Authorization": "token xxx"},
            "WS_URL":   "ws://host:port",
        }

    优先级：server_id 参数 > session 默认 > config.ini default
    session 限制：若 .session_servers 存在，server_id 必须在其中。
    """
    cfg = _load_cfg()

    # 确定目标 server_id
    if not server_id:
        server_id = get_default_server_id()

    if not server_id:
        raise ValueError("未找到任何服务器配置，请在 config.ini 中添加 [serverN] 节")

    # session 限制检查
    session_servers = get_session_servers()
    if session_servers is not None and server_id not in session_servers:
        raise PermissionError(
            f"服务器 '{server_id}' 不在本 session 的允许列表中\n"
            f"  允许的服务器: {', '.join(session_servers)}\n"
            f"  使用 'python cli.py session set ...' 修改 session 范围"
        )

    if not cfg.has_section(server_id):
        raise ValueError(
            f"服务器 '{server_id}' 不存在于 config.ini\n"
            f"  可用服务器: {[s['id'] for s in list_servers()]}"
        )

    host = cfg.get(server_id, "host")
    port = cfg.get(server_id, "port")
    token = cfg.get(server_id, "token")
    name = cfg.get(server_id, "name", fallback=server_id)

    base_url = f"http://{host}:{port}"
    return {
        "id": server_id,
        "name": name,
        "BASE_URL": base_url,
        "TOKEN": token,
        "HEADERS": {"Authorization": f"token {token}"},
        "WS_URL": base_url.replace("http", "ws"),
    }


def add_server(server_id: str, host: str, port: str, token: str, name: str = ""):
    """向 config.ini 添加新服务器"""
    cfg = _load_cfg()
    if cfg.has_section(server_id):
        raise ValueError(f"服务器 '{server_id}' 已存在")
    cfg.add_section(server_id)
    cfg.set(server_id, "host", host)
    cfg.set(server_id, "port", port)
    cfg.set(server_id, "token", token)
    if name:
        cfg.set(server_id, "name", name)
    # 如果是第一个服务器，设为 default
    if not cfg.has_section("servers"):
        cfg.add_section("servers")
    if not cfg.get("servers", "default", fallback=None):
        cfg.set("servers", "default", server_id)
    with open(_CONFIG_PATH, "w") as f:
        cfg.write(f)


def remove_server(server_id: str):
    """从 config.ini 删除服务器"""
    cfg = _load_cfg()
    if not cfg.has_section(server_id):
        raise ValueError(f"服务器 '{server_id}' 不存在")
    cfg.remove_section(server_id)
    # 若被删的是 default，清掉 default
    if cfg.get("servers", "default", fallback=None) == server_id:
        cfg.set("servers", "default", "")
    with open(_CONFIG_PATH, "w") as f:
        cfg.write(f)


def set_default_server(server_id: str):
    """设置默认服务器"""
    cfg = _load_cfg()
    if not cfg.has_section(server_id):
        raise ValueError(f"服务器 '{server_id}' 不存在")
    if not cfg.has_section("servers"):
        cfg.add_section("servers")
    cfg.set("servers", "default", server_id)
    with open(_CONFIG_PATH, "w") as f:
        cfg.write(f)


# ── 向后兼容：模块级变量（使用默认服务器） ──────────────────────────────────
# execute.py / notebook.py 等旧代码 import 这些变量时仍可工作
# 但推荐改为调用 get_server_config(server_id)
try:
    _default_cfg = get_server_config()
    BASE_URL = _default_cfg["BASE_URL"]
    TOKEN = _default_cfg["TOKEN"]
    HEADERS = _default_cfg["HEADERS"]
    WS_URL = _default_cfg["WS_URL"]
except Exception:
    BASE_URL = TOKEN = WS_URL = ""
    HEADERS = {}
