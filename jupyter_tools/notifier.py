"""
邮件通知模块

从 config.ini 的 [email] 节读取配置，在异步任务完成/失败时发送通知邮件。

配置示例（config.ini）：
    [email]
    enabled       = true
    smtp_host     = smtp.example.com
    smtp_port     = 465
    smtp_user     = your@email.com
    smtp_password = your_password
    to            = your@email.com, teammate@email.com
    from_name     = JupyterTool 通知
    only_on_error = false

不配置或 enabled = false 时完全跳过，不影响任何现有功能。
"""

import configparser
import os
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.ini")
_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", ".task_state.json")


def load_email_config() -> dict | None:
    """
    读取 config.ini 的 [email] 节。
    未配置、enabled=false 或缺少必填项时返回 None。
    """
    cfg = configparser.ConfigParser()
    cfg.read(_CONFIG_PATH)

    if not cfg.has_section("email"):
        return None

    enabled = cfg.get("email", "enabled", fallback="false").strip().lower()
    if enabled not in ("true", "1", "yes"):
        return None

    smtp_host = cfg.get("email", "smtp_host", fallback="").strip()
    smtp_port = cfg.get("email", "smtp_port", fallback="465").strip()
    smtp_user = cfg.get("email", "smtp_user", fallback="").strip()
    smtp_password = cfg.get("email", "smtp_password", fallback="").strip()
    to_raw = cfg.get("email", "to", fallback="").strip()

    # 必填项校验
    if not all([smtp_host, smtp_user, smtp_password, to_raw]):
        print("[⚠️ 邮件通知] config.ini [email] 缺少必填项（smtp_host/smtp_user/smtp_password/to），跳过发送")
        return None

    to_list = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
    if not to_list:
        return None

    return {
        "smtp_host": smtp_host,
        "smtp_port": int(smtp_port),
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
        "to": to_list,
        "from_name": cfg.get("email", "from_name", fallback="JupyterTool 通知").strip(),
        "only_on_error": cfg.get("email", "only_on_error", fallback="false").strip().lower() in ("true", "1", "yes"),
    }


def send_email(subject: str, body: str, cfg: dict):
    """
    发送邮件。
    端口 465 → SSL；其他端口 → STARTTLS。
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((cfg["from_name"], cfg["smtp_user"]))
    msg["To"] = ", ".join(cfg["to"])
    msg.attach(MIMEText(body, "plain", "utf-8"))

    port = cfg["smtp_port"]
    if port == 465:
        with smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=15) as server:
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(cfg["smtp_user"], cfg["to"], msg.as_string())
    else:
        with smtplib.SMTP(cfg["smtp_host"], port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(cfg["smtp_user"], cfg["to"], msg.as_string())


def send_task_notification(task_id: str, output: str, error: str):
    """
    任务完成/失败后发送邮件通知。
    邮件未配置或发送失败时静默跳过，不影响主流程。
    """
    try:
        email_cfg = load_email_config()
        if email_cfg is None:
            return

        is_error = bool(error)

        # only_on_error 模式：成功时不发
        if email_cfg["only_on_error"] and not is_error:
            return

        # 读取任务元信息
        import json
        task_info = {}
        try:
            with open(_STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
            task_info = state.get(task_id, {})
        except Exception:
            pass

        submit_time = task_info.get("submit_time", "未知")
        finish_time = task_info.get("finish_time", datetime.now().isoformat(timespec="seconds"))
        server_id = task_info.get("server_id") or "默认"
        code_snippet = task_info.get("code_snippet", "")

        # 计算耗时
        duration_str = ""
        try:
            t0 = datetime.fromisoformat(submit_time)
            t1 = datetime.fromisoformat(finish_time)
            secs = int((t1 - t0).total_seconds())
            duration_str = f"{secs // 3600}h {(secs % 3600) // 60}m {secs % 60}s" if secs >= 3600 \
                else f"{secs // 60}m {secs % 60}s" if secs >= 60 \
                else f"{secs}s"
        except Exception:
            pass

        # 组装主题
        status_tag = "❌ 失败" if is_error else "✅ 完成"
        subject = f"[JupyterTool] {status_tag}: {code_snippet[:40]}"

        # 组装正文
        output_preview = output[:2000] if output else "（无输出）"
        output_note = f"\n... (共 {len(output)} 字符，完整内容见 .task_logs/{task_id}.log)" \
            if len(output) > 2000 else ""

        lines = [
            f"任务 {status_tag}",
            "",
            f"任务 ID   : {task_id}",
            f"服务器    : {server_id}",
            f"提交时间  : {submit_time}",
            f"完成时间  : {finish_time}",
        ]
        if duration_str:
            lines.append(f"耗时      : {duration_str}")
        lines += [
            f"代码摘要  : {code_snippet}",
            "",
            "── 输出 ──────────────────────────────────",
            output_preview + output_note,
        ]
        if is_error:
            lines += [
                "",
                "── 错误 ──────────────────────────────────",
                error[:2000],
            ]

        body = "\n".join(lines)

        send_email(subject, body, email_cfg)
        print(f"[📧 邮件已发送] task_id={task_id}  收件人: {', '.join(email_cfg['to'])}", flush=True)

    except Exception as e:
        print(f"[⚠️ 邮件发送失败] {e}", flush=True)


def send_test_email() -> bool:
    """
    发送测试邮件，验证配置是否正确。
    返回 True 表示成功，False 表示失败（同时打印错误）。
    """
    email_cfg = load_email_config()
    if email_cfg is None:
        print("❌ 邮件通知未启用，请检查 config.ini 的 [email] 节")
        return False

    subject = "[JupyterTool] 测试邮件"
    body = (
        "这是一封来自 JupyterTool 的测试邮件。\n\n"
        "如果你收到此邮件，说明邮件通知配置正确。\n\n"
        f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"SMTP 服务器: {email_cfg['smtp_host']}:{email_cfg['smtp_port']}\n"
        f"收件人: {', '.join(email_cfg['to'])}\n"
    )

    try:
        send_email(subject, body, email_cfg)
        return True
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False
