---
name: jupyter-notebook
description: 操作远程 Jupyter 服务器，在 kernel 上执行 Python 代码、管理 notebook 文件、读写远程文件、修复脚本 bug、数据分析。当用户需要在远程 Jupyter 环境中执行代码、运行脚本、分析数据、增删文件、调试 notebook、查看服务器文件时使用。触发词：执行代码、跑一下、在 jupyter 上、运行脚本、修复 bug、查看 notebook、创建 notebook、远程执行、帮我跑、服务器上。
---

# Jupyter Notebook 工具集

工具目录：`/Users/huzhexin/Documents/jupyterTool/jupyter_tools/`
配置文件：`/Users/huzhexin/Documents/jupyterTool/config.ini`

所有操作通过 `cli.py` 执行。**默认不传 `--kernel` 时自动复用已保存的 Kernel，无需每次新建。**

## 快速参考

```bash
TOOLS=/Users/huzhexin/Documents/jupyterTool/jupyter_tools

# 执行代码（自动复用已保存 kernel）
python $TOOLS/cli.py execute --code "print('hello')"

# 强制新建 kernel
python $TOOLS/cli.py execute --kernel new --code "print('hello')"

# 执行 .py 文件
python $TOOLS/cli.py execute --file /path/to/script.py

# 列出运行中的 kernel
python $TOOLS/cli.py kernel list

# 查看当前保存的 kernel
python $TOOLS/cli.py kernel current

# 重启 kernel（清空变量）
python $TOOLS/cli.py kernel restart --id <KERNEL_ID>

# 删除 kernel
python $TOOLS/cli.py kernel delete --id <KERNEL_ID>

# 列出 notebook
python $TOOLS/cli.py notebook list --path subdir/

# 读取 notebook 所有代码
python $TOOLS/cli.py notebook get-code --path work/analysis.ipynb

# 追加 cell
python $TOOLS/cli.py notebook append --path work/analysis.ipynb --code "df.describe()"

# 远程文件操作
python $TOOLS/cli.py file list   --path some/dir
python $TOOLS/cli.py file read   --path data/script.py
python $TOOLS/cli.py file write  --path data/script.py --content "print('hello')"
python $TOOLS/cli.py file delete --path data/old.py
```

## 工作流

### 执行代码 / 数据分析

1. 首次用 `--kernel new`，后续直接省略 `--kernel`（自动复用）
2. 在同一 Kernel 内连续执行，变量和导入状态全程保持
3. 失败时读取 error，修复后重新执行
4. 长时间任务加 `--timeout 300`

### 修复远程脚本

1. `file read` 读取脚本
2. 分析错误，修改代码
3. `file write` 写回
4. `execute --file` 验证

### 查看 / 修改 Notebook

1. `notebook get-code` 提取所有 code cell
2. `notebook append` 追加新 cell
3. `execute` 验证

## 注意事项

- 不传 `--kernel` 时自动读取 `.kernel_state.json` 中保存的 ID
- 多行代码用 `--file` 而不是 `--content`（避免 shell 转义问题）
- 服务器地址和 token 在 `config.ini` 中配置
