"""
权限控制模块

从 config.ini [permissions] 读取配置：
- allowed_dirs:   允许操作的根目录白名单（路径必须在其中之一下）
- allow_delete:   是否允许删除操作
- protected_dirs: 即使 allow_delete=true，这些目录下也禁止删除
"""

import os
import configparser

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.ini")
_cfg = configparser.ConfigParser()
_cfg.read(_CONFIG_PATH)

def _parse_dirs(key: str) -> list[str]:
    raw = _cfg.get("permissions", key, fallback="").strip()
    if not raw:
        return []
    return [d.strip() for d in raw.split(",") if d.strip()]

_allowed_dirs   = _parse_dirs("allowed_dirs")
_protected_dirs = _parse_dirs("protected_dirs")
_allow_delete   = _cfg.getboolean("permissions", "allow_delete", fallback=True)


class PermissionError(Exception):
    pass


def _normalize(path: str) -> str:
    """统一路径格式，去掉末尾斜杠"""
    return os.path.normpath(path.strip())


def check_path_allowed(path: str):
    """
    检查路径是否在 allowed_dirs 白名单内。
    allowed_dirs 为空时不限制。
    """
    if not _allowed_dirs:
        return
    norm = _normalize(path)
    for d in _allowed_dirs:
        nd = _normalize(d)
        if norm == nd or norm.startswith(nd + os.sep):
            return
    raise PermissionError(
        f"❌ 路径不在允许范围内: {path}\n"
        f"   允许的目录: {', '.join(_allowed_dirs)}"
    )


def check_delete_allowed(path: str):
    """
    检查是否允许删除该路径：
    1. allow_delete 必须为 true
    2. 路径不能在 protected_dirs 下
    """
    if not _allow_delete:
        raise PermissionError(
            f"❌ 删除操作已被禁用（allow_delete = false）\n"
            f"   如需开启，请修改 config.ini 中的 allow_delete = true"
        )
    norm = _normalize(path)
    for d in _protected_dirs:
        nd = _normalize(d)
        if norm == nd or norm.startswith(nd + os.sep):
            raise PermissionError(
                f"❌ 路径在保护目录下，禁止删除: {path}\n"
                f"   保护目录: {d}"
            )


def check_write_allowed(path: str):
    """检查写入权限（路径必须在 allowed_dirs 内）"""
    check_path_allowed(path)


def print_permissions():
    """打印当前权限配置，供调试使用"""
    print("[权限配置]")
    print(f"  允许操作目录: {_allowed_dirs or '不限制'}")
    print(f"  允许删除:     {_allow_delete}")
    print(f"  保护目录:     {_protected_dirs or '无'}")
