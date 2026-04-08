---
name: jupyter-notebook
description: 操作远程 Jupyter 服务器，在 kernel 上执行 Python 代码、管理 notebook 文件、读写远程文件、修复脚本 bug、数据分析。当用户需要在远程 Jupyter 环境中执行代码、运行脚本、分析数据、增删文件、调试 notebook、查看服务器文件时使用。触发词：执行代码、跑一下、在 jupyter 上、运行脚本、修复 bug、查看 notebook、创建 notebook、远程执行、帮我跑、服务器上。
---

# Jupyter Notebook 工具集

工具目录由安装时写入 `~/.claude/skills/jupyter-notebook/.tools_path`，读取方式：

```bash
TOOLS=$(cat ~/.claude/skills/jupyter-notebook/.tools_path)
```

配置文件：`$TOOLS/../config.ini`（即项目根目录下的 `config.ini`）

所有操作通过 `cli.py` 执行。**默认不传 `--kernel` 时自动复用已保存的 Kernel，无需每次新建。**

## 多服务器支持

`config.ini` 支持配置多台服务器（`[server1]`、`[server2]` ...），通过 `--server <ID>` 指定目标服务器，不填则使用默认服务器。

每个对话窗口可通过 `session set` 限定只访问特定服务器，Kernel 状态按服务器隔离。

## 快速参考

```bash
TOOLS=$(cat ~/.claude/skills/jupyter-notebook/.tools_path)

# 执行代码（自动复用已保存 kernel，使用默认服务器）
python $TOOLS/cli.py execute --code "print('hello')"

# 指定服务器执行
python $TOOLS/cli.py --server server2 execute --code "print('hello')"

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

# 服务器管理
python $TOOLS/cli.py server list
python $TOOLS/cli.py server add --id server2 --host 10.0.0.1 --port 8888 --token xxx --name "训练机B"
python $TOOLS/cli.py server default --id server2

# Session 范围管理
python $TOOLS/cli.py session set server1 server2   # 本 session 只允许访问这些服务器
python $TOOLS/cli.py session list
python $TOOLS/cli.py session clear
```

## 工作流

### 执行代码 / 数据分析

1. 首次用 `--kernel new`，后续直接省略 `--kernel`（自动复用）
2. 在同一 Kernel 内连续执行，变量和导入状态全程保持
3. 失败时读取 error，修复后重新执行
4. 长时间任务加 `--timeout 300`

### 多服务器操作

1. `server list` 查看所有已配置服务器
2. 用 `--server <ID>` 切换目标服务器
3. 不同服务器的 Kernel 相互独立，互不干扰
4. 需要动态添加新服务器时用 `server add`

### Session 范围限制

当一个对话窗口只应操作特定服务器时：

1. `session set server1` 设置限制
2. 此后所有操作（包括 `--server` 指定的）都只能访问 server1
3. `session clear` 解除限制

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

- 不传 `--kernel` 时自动读取 `.kernel_state.json` 中保存的 ID（按服务器隔离）
- 多行代码用 `--file` 而不是 `--code`（避免 shell 转义问题）
- 服务器地址和 token 在项目根目录的 `config.ini` 中配置
- `--server` 必须写在子命令之前：`python cli.py --server server2 execute ...`
