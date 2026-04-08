"""
Claude Code 直接调用示例：

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
"""

import argparse
import json
import sys
from kernel import create_kernel, list_kernels, restart_kernel, delete_kernel, get_or_create_kernel, save_kernel_id, load_kernel_id, clear_kernel_id
from execute import execute_code, execute_file
from notebook import (
    list_notebooks, list_directory, read_notebook, append_cell, get_all_code,
    create_notebook, write_file, read_file, delete_file
)
from file import save_result, save_markdown_report


def main():
    parser = argparse.ArgumentParser(description="Jupyter Tools for Claude Code")
    subparsers = parser.add_subparsers(dest="command")

    # kernel 子命令
    k = subparsers.add_parser("kernel", help="Kernel 管理")
    k.add_argument("action", choices=["list", "create", "restart", "delete", "save", "current", "clear"])
    k.add_argument("--id", help="Kernel ID")
    k.add_argument("--name", default="python3", help="Kernel 类型（默认 python3）")

    # execute 子命令
    e = subparsers.add_parser("execute", help="执行代码")
    e.add_argument("--kernel", default="new", help="Kernel ID 或 'new'")
    e.add_argument("--code", help="直接传入代码字符串")
    e.add_argument("--file", help="传入 .py 文件路径")
    e.add_argument("--save", help="结果保存路径（.json 或 .md）")
    e.add_argument("--timeout", type=int, default=60, help="超时秒数（默认 60）")

    # notebook 子命令
    n = subparsers.add_parser("notebook", help="Notebook 文件操作")
    n.add_argument("action", choices=["list", "read", "append", "get-code", "create"])
    n.add_argument("--path", help="Notebook 路径")
    n.add_argument("--code", help="追加的代码")
    n.add_argument("--type", default="code", choices=["code", "markdown"], help="Cell 类型")

    # file 子命令（远程文件操作）
    f = subparsers.add_parser("file", help="远程文件操作")
    f.add_argument("action", choices=["list", "read", "write", "delete"])
    f.add_argument("--path", help="文件或目录路径")
    f.add_argument("--content", help="写入内容（write 时使用）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # kernel 操作
    if args.command == "kernel":
        if args.action == "list":
            kernels = list_kernels()
            if not kernels:
                print("（无运行中的 Kernel）")
        elif args.action == "create":
            kid = create_kernel(args.name)
            print(f"KERNEL_ID={kid}")
        elif args.action == "restart":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            restart_kernel(args.id)
        elif args.action == "delete":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            delete_kernel(args.id)
        elif args.action == "save":
            if not args.id:
                print("❌ 请指定 --id")
                sys.exit(1)
            save_kernel_id(args.id)
            print(f"[💾 已保存 Kernel ID] {args.id}")
        elif args.action == "current":
            kid = load_kernel_id()
            if kid:
                print(f"KERNEL_ID={kid}")
            else:
                print("（无已保存的 Kernel ID）")
        elif args.action == "clear":
            clear_kernel_id()
            print("[🗑 已清除保存的 Kernel ID]")

    # 执行代码
    elif args.command == "execute":
        kernel_id = get_or_create_kernel(
            None if args.kernel == "new" else args.kernel
        )
        print(f"KERNEL_ID={kernel_id}")

        if args.code:
            result = execute_code(kernel_id, args.code, args.timeout)
        elif args.file:
            result = execute_file(kernel_id, args.file, args.timeout)
        else:
            print("❌ 请指定 --code 或 --file")
            sys.exit(1)

        print("\n" + "=" * 50)
        if result["success"]:
            print(f"✅ 执行成功")
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

    # notebook 操作
    elif args.command == "notebook":
        if args.action == "list":
            notebooks = list_notebooks(args.path or "")
            if not notebooks:
                print("（无 Notebook 文件）")
        elif args.action == "read":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            nb = read_notebook(args.path)
            print(json.dumps(nb, ensure_ascii=False, indent=2))
        elif args.action == "append":
            if not args.path or not args.code:
                print("❌ 请指定 --path 和 --code")
                sys.exit(1)
            append_cell(args.path, args.code, args.type)
        elif args.action == "get-code":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            print(get_all_code(args.path))
        elif args.action == "create":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            create_notebook(args.path)

    # 远程文件操作
    elif args.command == "file":
        if args.action == "list":
            list_directory(args.path or "")
        elif args.action == "read":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            content = read_file(args.path)
            print(content)
        elif args.action == "write":
            if not args.path or args.content is None:
                print("❌ 请指定 --path 和 --content")
                sys.exit(1)
            write_file(args.path, args.content)
        elif args.action == "delete":
            if not args.path:
                print("❌ 请指定 --path")
                sys.exit(1)
            delete_file(args.path)


if __name__ == "__main__":
    main()
