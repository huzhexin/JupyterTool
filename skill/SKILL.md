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

## 同步 vs 异步：Agent 自主决策规则

**默认使用同步阻塞**，执行完立即获得结果，可直接分析输出、修复 bug、继续下一步。

**满足以下任一条件时，主动切换为异步模式（`--async`）：**

| 判断依据 | 说明 |
|---------|------|
| 预期执行超过 30 分钟 | 训练、全量评估、大规模批处理 |
| 代码含大循环：`for epoch in range(N)`，N 较大 | 多轮训练 |
| 代码含 `time.sleep` 或明显的长时等待 | 轮询任务、定时任务 |
| 用户明确提到"跑完通知我"/"后台跑" | 用户意图 |
| timeout 需要设置超过 1800 秒 | 超长任务 |

**异步模式流程：**
1. `execute --async` 立即返回 `TASK_ID`，不阻塞
2. 用 `task logs --id <TASK_ID>` 查看实时进度
3. 用 `task status --id <TASK_ID>` 确认完成状态

## 多服务器支持

`config.ini` 支持配置多台服务器（`[server1]`、`[server2]` ...），通过 `--server <ID>` 指定目标服务器，不填则使用默认服务器。

每个对话窗口可通过 `session set` 限定只访问特定服务器，Kernel 状态按服务器隔离。

## 快速参考

```bash
TOOLS=$(cat ~/.claude/skills/jupyter-notebook/.tools_path)

# ── 同步执行（默认，适合短时任务）──────────────────────────────────────────
# 执行代码（自动复用已保存 kernel）
python $TOOLS/cli.py execute --code "print('hello')"

# 指定服务器执行
python $TOOLS/cli.py --server server2 execute --code "print('hello')"

# 强制新建 kernel
python $TOOLS/cli.py execute --kernel new --code "print('hello')"

# 执行 .py 文件
python $TOOLS/cli.py execute --file /path/to/script.py

# 自定义超时（秒）
python $TOOLS/cli.py execute --code "..." --timeout 300

# ── 异步执行（适合长时间任务）──────────────────────────────────────────────
# 提交异步任务，立即返回 TASK_ID
python $TOOLS/cli.py execute --file /path/to/train.py --async --timeout 7200

# 查看任务实时日志（全量）
python $TOOLS/cli.py task logs --id <TASK_ID>

# 查看最后 50 行日志
python $TOOLS/cli.py task logs --id <TASK_ID> --tail 50

# 查看任务状态 + 输出摘要
python $TOOLS/cli.py task status --id <TASK_ID>

# 列出所有任务
python $TOOLS/cli.py task list

# 取消正在运行的任务
python $TOOLS/cli.py task cancel --id <TASK_ID>

# 清理已完成的历史记录
python $TOOLS/cli.py task clean

# ── 回调服务（可选，减少轮询）──────────────────────────────────────────────
# 启动本地回调服务（端口 18888，异步任务完成后主动通知）
python $TOOLS/cli.py callback start

# 查看回调服务状态
python $TOOLS/cli.py callback status

# 停止回调服务
python $TOOLS/cli.py callback stop

# ── Kernel 管理 ─────────────────────────────────────────────────────────────
python $TOOLS/cli.py kernel list
python $TOOLS/cli.py kernel current
python $TOOLS/cli.py kernel restart --id <KERNEL_ID>
python $TOOLS/cli.py kernel delete --id <KERNEL_ID>

# ── Notebook 操作 ───────────────────────────────────────────────────────────
python $TOOLS/cli.py notebook list --path subdir/
python $TOOLS/cli.py notebook get-code --path work/analysis.ipynb
python $TOOLS/cli.py notebook append --path work/analysis.ipynb --code "df.describe()"

# ── 远程文件操作 ─────────────────────────────────────────────────────────────
python $TOOLS/cli.py file list   --path some/dir
python $TOOLS/cli.py file read   --path data/script.py
python $TOOLS/cli.py file write  --path data/script.py --content "print('hello')"
python $TOOLS/cli.py file delete --path data/old.py

# ── 服务器管理 ──────────────────────────────────────────────────────────────
python $TOOLS/cli.py server list
python $TOOLS/cli.py server add --id server2 --host 10.0.0.1 --port 8888 --token xxx --name "训练机B"
python $TOOLS/cli.py server default --id server2

# ── Session 范围管理 ─────────────────────────────────────────────────────────
python $TOOLS/cli.py session set server1 server2
python $TOOLS/cli.py session list
python $TOOLS/cli.py session clear
```

## 工作流

### 执行代码 / 数据分析（同步）

1. 首次用 `--kernel new`，后续直接省略 `--kernel`（自动复用）
2. 在同一 Kernel 内连续执行，变量和导入状态全程保持
3. 失败时读取 error，修复后重新执行
4. 执行完成后日志自动保存到 `.task_logs/<task_id>.log`，可回溯

### 长时间训练任务（异步）

1. 判断任务是否满足异步条件（见上方决策规则）
2. 用 `--async` 提交，记录返回的 `TASK_ID`
3. 告知用户任务已提交，继续处理其他问题
4. 需要时用 `task logs` 查看进度，`task status` 确认完成
5. 完成后读取输出，继续后续分析

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

## 邮件通知配置

异步任务完成/失败后可自动发送邮件。在 `config.ini` 中添加 `[email]` 节启用：

```ini
[email]
enabled       = true
smtp_host     = smtp.qq.com       # QQ邮箱示例
smtp_port     = 465
smtp_user     = your@qq.com
smtp_password = your_auth_code    # QQ/163邮箱需使用授权码，非登录密码
to            = your@email.com
only_on_error = false             # true = 只在失败时发邮件
```

配置完成后用测试命令验证：

```bash
python $TOOLS/cli.py email test
```

**不配置或 `enabled = false` 时完全跳过，不影响任何现有功能。**

常用 SMTP 参数：

| 邮箱 | smtp_host | smtp_port | 密码说明 |
|------|-----------|-----------|---------|
| QQ 邮箱 | smtp.qq.com | 465 | 需开启 SMTP，使用授权码 |
| 163 邮箱 | smtp.163.com | 465 | 需开启 SMTP，使用授权码 |
| Gmail | smtp.gmail.com | 587 | 需开启两步验证，使用应用密码 |
| 企业微信邮箱 | smtp.exmail.qq.com | 465 | 使用邮箱密码 |

## 注意事项

- 不传 `--kernel` 时自动读取 `.kernel_state.json` 中保存的 ID（按服务器隔离）
- 多行代码用 `--file` 而不是 `--code`（避免 shell 转义问题）
- 服务器地址和 token 在项目根目录的 `config.ini` 中配置
- `--server` 必须写在子命令之前：`python cli.py --server server2 execute ...`
- 异步模式默认 timeout 为 7200 秒（2 小时），超长任务可继续调大
- 回调服务（`callback start`）需要 Jupyter 服务器能访问本机，内网隔离时可跳过，改用 `task logs` 轮询
- 邮件通知仅在异步任务（`--async`）完成时触发，同步执行不发邮件
