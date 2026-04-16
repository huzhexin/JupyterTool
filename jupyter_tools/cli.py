"""
Claude Code 直接调用示例：

# 基本用法（使用默认服务器）
python cli.py execute --kernel new --code "print(1+1)"
python cli.py execute --kernel abc123 --file my_code.py
python cli.py execute --kernel new --code "print(1+1)" --timeout 120
python cli.py kernel list
python cli.py kernel create
python cli.py kernel restart --id abc123
python cli.py kernel delete --id abc123
python cli.py notebook list
python cli.py notebook list --path some/subdir
python cli.py notebook read --path work/analysis.ipynb
python cli.py notebook append --path work/analysis.ipynb --code "print('hello')"
python cli.py notebook get-code --path work/analysis.ipynb
python cli.py notebook create --path work/new.ipynb
python cli.py file list --path some/dir
python cli.py file write --path data/script.py --content "print('hello')"
python cli.py file read --path data/script.py
python cli.py file delete --path data/old.py

# 指定服务器
python cli.py --server server2 execute --kernel new --code "print(1+1)"
python cli.py --server server2 kernel list

# 服务器管理
python cli.py server list
python cli.py server add --id server2 --host 10.10.20.30 --port 8420 --token yyy --name "训练机B"
python cli.py server remove --id server2
python cli.py server default --id server2

# Session 范围管理（限制本对话窗口只能访问特定服务器）
python cli.py session set server1 server2
python cli.py session list
python cli.py session clear
"""

import argparse
import json
import os
import sys
from config import (
    list_servers, add_server, remove_server, set_default_server,
    get_session_servers, set_session_servers, clear_session_servers
)
from kernel import create_kernel, list_kernels, restart_kernel, delete_kernel, get_or_create_kernel, save_kernel_id, load_kernel_id, clear_kernel_id
from execute import execute_code, execute_file
from task import (
    create_task, list_tasks, get_task, clean_tasks,
    print_task, read_task_logs
)
from worker import submit_async
from callback_server import (
    is_running as cb_is_running, stop_server as cb_stop,
    read_pid as cb_read_pid, CALLBACK_PORT
)
from notebook import (
    list_notebooks, list_directory, read_notebook, append_cell, get_all_code,
    create_notebook, write_file, read_file, delete_file
)
from file import save_result, save_markdown_report
from notifier import send_test_email
from permissions import print_permissions, PermissionError as JupyterPermissionError


def main():
    parser = argparse.ArgumentParser(description="Jupyter Tools for Claude Code")

    # 全局 --server 参数
    parser.add_argument(
        "--server", default=None,
        help="指定目标服务器 ID（如 server1、server2），不填则使用默认服务器"
    )

    subparsers = parser.add_subparsers(dest="command")

    # ── kernel 子命令 ────────────────────────────────────────────────────────
    k = subparsers.add_parser("kernel", help="Kernel 管理")
    k.add_argument("action", choices=["list", "create", "restart", "delete", "save", "current", "clear"])
    k.add_argument("--id", help="Kernel ID")
    k.add_argument("--name", default="python3", help="Kernel 类型（默认 python3）")

    # ── execute 子命令 ───────────────────────────────────────────────────────
    e = subparsers.add_parser("execute", help="执行代码")
    e.add_argument("--kernel", default="new", help="Kernel ID 或 'new'")
    e.add_argument("--code", help="直接传入代码字符串")
    e.add_argument("--file", help="传入 .py 文件路径")
    e.add_argument("--save", help="结果保存路径（.json 或 .md）")
    e.add_argument("--timeout", type=int, default=60, help="超时秒数（默认 60）")
    e.add_argument("--async", dest="run_async", action="store_true",
                   help="异步执行：立即返回 task_id，不等待完成（适合长时间任务）")

    # ── task 子命令 ──────────────────────────────────────────────────────────
    ta = subparsers.add_parser("task", help="异步任务管理")
    ta.add_argument("action", choices=["list", "status", "cancel", "logs", "clean"])
    ta.add_argument("--id", help="任务 ID")
    ta.add_argument("--tail", type=int, default=None, help="logs 时只显示最后 N 行")

    # ── callback 子命令 ──────────────────────────────────────────────────────
    cb = subparsers.add_parser("callback", help="本地回调服务管理")
    cb.add_argument("action", choices=["start", "stop", "status"])

    # ── email 子命令 ─────────────────────────────────────────────────────────
    subparsers.add_parser("email", help="邮件通知管理").add_argument(
        "action", choices=["test"], help="test: 发送测试邮件验证配置"
    )

    # ── notebook 子命令 ──────────────────────────────────────────────────────
    n = subparsers.add_parser("notebook", help="Notebook 文件操作")
    n.add_argument("action", choices=["list", "read", "append", "get-code", "create"])
    n.add_argument("--path", help="Notebook 路径")
    n.add_argument("--code", help="追加的代码")
    n.add_argument("--type", default="code", choices=["code", "markdown"], help="Cell 类型")

    # ── file 子命令（远程文件操作） ──────────────────────────────────────────
    f = subparsers.add_parser("file", help="远程文件操作")
    f.add_argument("action", choices=["list", "read", "write", "delete"])
    f.add_argument("--path", help="文件或目录路径")
    f.add_argument("--content", help="写入内容（write 时使用）")

    # ── server 子命令 ────────────────────────────────────────────────────────
    sv = subparsers.add_parser("server", help="服务器管理")
    sv.add_argument("action", choices=["list", "add", "remove", "default"])
    sv.add_argument("--id", help="服务器 ID（如 server2）")
    sv.add_argument("--host", help="服务器主机地址")
    sv.add_argument("--port", help="服务器端口")
    sv.add_argument("--token", help="Jupyter Token")
    sv.add_argument("--name", default="", help="服务器显示名称（可选）")

    # ── session 子命令 ───────────────────────────────────────────────────────
    ss = subparsers.add_parser(
        "session",
        help="Session 范围管理（限制本对话窗口只能访问特定服务器）"
    )
    ss.add_argument("action", choices=["set", "list", "clear"])
    ss.add_argument("servers", nargs="*", help="服务器 ID 列表（set 时使用）")

    # ── permissions 子命令 ───────────────────────────────────────────────────
    subparsers.add_parser("permissions", help="查看当前权限配置")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    server_id = args.server  # 全局 --server 参数

    # ── kernel 操作 ──────────────────────────────────────────────────────────
    if args.command == "kernel":
        if args.action == "list":
            kernels = list_kernels(server_id)
            if not kernels:
                print("（无运行中的 Kernel）")
        elif args.action == "create":
            kid = create_kernel(args.name, server_id)
            print(f"KERNEL_ID={kid}")
        elif args.action == "restart":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            restart_kernel(args.id, server_id)
        elif args.action == "delete":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            delete_kernel(args.id, server_id)
        elif args.action == "save":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            save_kernel_id(args.id, server_id)
            print(f"[💾 已保存 Kernel ID] {args.id}")
        elif args.action == "current":
            kid = load_kernel_id(server_id)
            if kid:
                print(f"KERNEL_ID={kid}")
            else:
                print("（无已保存的 Kernel ID）")
        elif args.action == "clear":
            clear_kernel_id(server_id)
            print("[🗑 已清除保存的 Kernel ID]")

    # ── 执行代码 ─────────────────────────────────────────────────────────────
    elif args.command == "execute":
        import uuid as _uuid
        kernel_id = get_or_create_kernel(
            None if args.kernel == "new" else args.kernel,
            server_id
        )
        print(f"KERNEL_ID={kernel_id}")

        # 读取代码内容（--code 或 --file）
        if args.code:
            code_content = args.code
        elif args.file:
            with open(args.file, "r", encoding="utf-8") as _f:
                code_content = _f.read()
            print(f"[📄 执行文件] {args.file}")
        else:
            print("❌ 请指定 --code 或 --file")
            sys.exit(1)

        if args.run_async:
            # ── 异步模式：立即返回 task_id ──────────────────────────────────
            task_id = _uuid.uuid4().hex[:12]
            create_task(task_id, kernel_id, server_id or "", code_content)
            submit_async(task_id, kernel_id, code_content,
                         timeout=args.timeout, server_id=server_id)
            print(f"\n[🚀 异步任务已提交]")
            print(f"TASK_ID={task_id}")
            print(f"  日志: python cli.py task logs --id {task_id}")
            print(f"  状态: python cli.py task status --id {task_id}")
        else:
            # ── 同步模式：阻塞等待结果 ───────────────────────────────────────
            task_id = _uuid.uuid4().hex[:12]
            if args.code:
                result = execute_code(kernel_id, code_content, args.timeout,
                                      server_id, task_id=task_id)
            else:
                result = execute_file(kernel_id, args.file, args.timeout,
                                      server_id, task_id=task_id)

            print("\n" + "=" * 50)
            if result["success"]:
                print(f"✅ 执行成功  (日志: .task_logs/{task_id}.log)")
                if result["output"]:
                    print(result["output"])
            else:
                print(f"❌ 执行失败")
                if result["error"]:
                    print(result["error"])

            if result.get("displays"):
                print(f"\n[图表输出: {len(result['displays'])} 个]")

            if args.save:
                if args.save.endswith(".md"):
                    save_markdown_report(args.code or args.file, result, args.save)
                else:
                    save_result(result, args.save)

    # ── notebook 操作 ────────────────────────────────────────────────────────
    elif args.command == "notebook":
        if args.action == "list":
            notebooks = list_notebooks(args.path or "", server_id)
            if not notebooks:
                print("（无 Notebook 文件）")
        elif args.action == "read":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            nb = read_notebook(args.path, server_id)
            print(json.dumps(nb, ensure_ascii=False, indent=2))
        elif args.action == "append":
            if not args.path or not args.code:
                print("❌ 请指定 --path 和 --code")
                sys.exit(1)
            append_cell(args.path, args.code, args.type, server_id)
        elif args.action == "get-code":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            print(get_all_code(args.path, server_id))
        elif args.action == "create":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            create_notebook(args.path, server_id=server_id)

    # ── 远程文件操作 ─────────────────────────────────────────────────────────
    elif args.command == "file":
        if args.action == "list":
            list_directory(args.path or "", server_id)
        elif args.action == "read":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            content = read_file(args.path, server_id)
            print(content)
        elif args.action == "write":
            if not args.path or args.content is None:
                print("❌ 请指定 --path 和 --content")
                sys.exit(1)
            write_file(args.path, args.content, server_id)
        elif args.action == "delete":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            delete_file(args.path, server_id)

    # ── 服务器管理 ───────────────────────────────────────────────────────────
    elif args.command == "server":
        if args.action == "list":
            servers = list_servers()
            if not servers:
                print("（无已配置的服务器）")
            else:
                print("[已配置的服务器]")
                for s in servers:
                    default_tag = " [默认]" if s["is_default"] else ""
                    name_tag = f" ({s['name']})" if s["name"] != s["id"] else ""
                    print(f"  {s['id']}{default_tag}{name_tag}  {s['host']}:{s['port']}")
        elif args.action == "add":
            if not all([args.id, args.host, args.port, args.token]):
                print("❌ 请指定 --id --host --port --token")
                sys.exit(1)
            add_server(args.id, args.host, args.port, args.token, args.name)
            print(f"[✅ 服务器已添加] {args.id}  {args.host}:{args.port}")
        elif args.action == "remove":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            remove_server(args.id)
            print(f"[🗑 服务器已删除] {args.id}")
        elif args.action == "default":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            set_default_server(args.id)
            print(f"[⭐ 默认服务器已设置] {args.id}")

    # ── Session 范围管理 ─────────────────────────────────────────────────────
    elif args.command == "session":
        if args.action == "set":
            if not args.servers:
                print("❌ 请提供至少一个服务器 ID，例如: session set server1 server2")
                sys.exit(1)
            # 校验 server ID 是否存在
            available = {s["id"] for s in list_servers()}
            unknown = [s for s in args.servers if s not in available]
            if unknown:
                print(f"❌ 未知服务器: {', '.join(unknown)}")
                print(f"   可用服务器: {', '.join(sorted(available))}")
                sys.exit(1)
            set_session_servers(args.servers)
            print(f"[🔒 Session 范围已设置] 允许服务器: {', '.join(args.servers)}")
        elif args.action == "list":
            session = get_session_servers()
            if session is None:
                print("（Session 无限制，可访问所有服务器）")
            else:
                print(f"[本 Session 允许的服务器] {', '.join(session)}")
        elif args.action == "clear":
            clear_session_servers()
            print("[🔓 Session 限制已清除]")

    # ── 异步任务管理 ─────────────────────────────────────────────────────────
    elif args.command == "task":
        if args.action == "list":
            tasks = list_tasks()
            if not tasks:
                print("（无任务记录）")
            else:
                print(f"[任务列表] 共 {len(tasks)} 条")
                for t in tasks:
                    print_task(t["task_id"], t)
        elif args.action == "status":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            info = get_task(args.id)
            if not info:
                print(f"❌ 未找到任务: {args.id}")
                sys.exit(1)
            print_task(args.id, info)
            if info["output"]:
                print("\n[输出]")
                print(info["output"][:2000])
                if len(info["output"]) > 2000:
                    print(f"  ... (共 {len(info['output'])} 字符，用 task logs 查看完整日志)")
            if info["error"]:
                print("\n[错误]")
                print(info["error"])
        elif args.action == "cancel":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            info = get_task(args.id)
            if not info:
                print(f"❌ 未找到任务: {args.id}")
                sys.exit(1)
            if info["status"] != "running":
                print(f"⚠️  任务 {args.id} 状态为 {info['status']}，无需取消")
            else:
                from kernel import interrupt_kernel
                interrupt_kernel(info["kernel_id"], info["server_id"] or None)
                print(f"[⏹ 已发送中断信号] task_id={args.id}")
        elif args.action == "logs":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            logs = read_task_logs(args.id, tail=args.tail)
            if not logs:
                print(f"（暂无日志: {args.id}）")
            else:
                print(logs, end="")
        elif args.action == "clean":
            removed = clean_tasks()
            print(f"[🗑 已清理 {removed} 条已完成任务记录]")

    # ── 本地回调服务管理 ──────────────────────────────────────────────────────
    elif args.command == "callback":
        if args.action == "start":
            if cb_is_running():
                pid = cb_read_pid()
                print(f"[⚠️  Callback Server 已在运行] PID={pid}  端口={CALLBACK_PORT}")
            else:
                import subprocess
                cb_script = os.path.join(os.path.dirname(__file__), "callback_server.py")
                proc = subprocess.Popen(
                    [sys.executable, cb_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                print(f"[🌐 Callback Server 已启动] PID={proc.pid}  端口={CALLBACK_PORT}")
        elif args.action == "stop":
            cb_stop()
        elif args.action == "status":
            if cb_is_running():
                pid = cb_read_pid()
                print(f"[✅ Callback Server 运行中] PID={pid}  端口={CALLBACK_PORT}")
            else:
                print(f"[🔴 Callback Server 未运行]  端口={CALLBACK_PORT}")

    # ── 邮件通知管理 ──────────────────────────────────────────────────────────
    elif args.command == "email":
        if args.action == "test":
            ok = send_test_email()
            if ok:
                print("✅ 测试邮件已发送，请检查收件箱")
            else:
                sys.exit(1)

    # ── 权限配置 ─────────────────────────────────────────────────────────────
    elif args.command == "permissions":
        print_permissions()


if __name__ == "__main__":
    try:
        main()
    except JupyterPermissionError as e:
        print(e)
        sys.exit(1)
    except (ValueError, PermissionError) as e:
        print(e)
        sys.exit(1)
