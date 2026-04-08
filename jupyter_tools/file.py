import json
import base64
from datetime import datetime


def save_result(result: dict, filepath: str = "result.json"):
    """保存执行结果为 JSON"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[💾 结果已保存] {filepath}")


def load_result(filepath: str = "result.json") -> dict:
    """读取执行结果"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_image(b64_data: str, filepath: str = None):
    """保存 base64 图片"""
    filepath = filepath or f"output_{datetime.now().strftime('%H%M%S')}.png"
    with open(filepath, "wb") as f:
        f.write(base64.b64decode(b64_data))
    print(f"[🖼 图片已保存] {filepath}")
    return filepath


def save_markdown_report(code: str, result: dict, filepath: str = "report.md"):
    """将代码+结果保存为 Markdown 报告"""
    lines = [
        f"# 执行报告 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 代码",
        "```python",
        code,
        "```",
        "",
        f"## 状态: {'✅ 成功' if result['success'] else '❌ 失败'}",
        "",
    ]

    if result["output"]:
        lines += ["## 输出", "```", result["output"], "```", ""]

    if result["error"]:
        lines += ["## 错误", "```", result["error"], "```", ""]

    if result.get("displays"):
        lines += [f"## 图表输出: {len(result['displays'])} 个", ""]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[📄 报告已保存] {filepath}")
    return filepath
