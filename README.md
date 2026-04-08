# JupyterTool

让 Claude Code 直接操作远程 Jupyter 服务器——执行代码、管理 Kernel、读写文件、调试脚本，全程用自然语言驱动。支持同时管理多台 Jupyter 服务器，每个对话窗口可独立限定访问范围。目前个人使用，可能存在bug，出问题别找我 ^_^

## 项目结构

```
jupyterTool/
├── config.ini              # 服务器配置 + 权限配置
├── install.sh              # 一键安装 Skill
├── jupyter_tools/          # 核心工具代码
│   ├── config.py           # 多服务器配置读取
│   ├── kernel.py           # Kernel 管理 + 状态持久化（按服务器隔离）
│   ├── execute.py          # 代码执行（WebSocket）
│   ├── notebook.py         # Notebook & 远程文件操作
│   ├── permissions.py      # 权限控制（路径白名单、删除开关）
│   ├── file.py             # 本地结果保存
│   ├── cli.py              # 命令行入口
│   ├── .kernel_state.json  # 自动生成，按服务器记录 Kernel ID
│   └── ..session_servers   # 自动生成，记录本 session 的服务器范围
└── skill/
    └── SKILL.md            # Claude Code Skill 定义
```

## 配置

编辑项目根目录的 `config.ini`：

```ini
[servers]
# 默认使用的服务器 ID
default = server1

[server1]
host  = your-host
port  = 8420
token = your-jupyter-token
name  = 训练机A          # 可选，显示名称

[server2]
host  = another-host
port  = 8888
token = another-token
name  = 训练机B

[permissions]
# 允许操作的根目录（逗号分隔），留空表示不限制
allowed_dirs = /mnt/your/work/dir

# 是否允许删除操作（true/false）
allow_delete = false

# 即使开了 allow_delete，这些目录下也永远禁止删除
protected_dirs = /mnt/your/important/dir
```

## Vibe Coding 教程

> 配置好之后，你不需要记任何命令。直接用中文告诉 Claude 你想做什么，它会自动调用工具完成。

### 第一步：安装 Skill

在项目根目录执行，自动安装 Skill 并记录工具路径：

```bash
bash install.sh
```

安装脚本会：
1. 复制 `skill/` 到 `~/.claude/skills/jupyter-notebook/`
2. 将当前 `jupyter_tools/` 的绝对路径写入 `~/.claude/skills/jupyter-notebook/.tools_path`，供 Claude 调用时定位工具

### 第二步：直接说话

打开 Claude Code，像聊天一样描述你的需求：

---

**场景 1：执行代码**

> "在 Jupyter 上跑一下 `print('hello world')`"

Claude 会自动新建 Kernel、执行代码、返回结果。

---

**场景 2：数据分析**

> "帮我加载 /data/sales.csv，看一下数据结构，然后统计每个月的销售额"

Claude 会：
1. 新建 Kernel，`import pandas as pd`
2. 读取 CSV，打印 `df.shape` / `df.dtypes`
3. 按月聚合，返回结果
4. 全程复用同一个 Kernel，变量保持

---

**场景 3：修复远程脚本**

> "我的训练脚本 /mnt/data/train.py 跑报错了，帮我看看"

Claude 会：
1. 读取脚本内容
2. 执行并捕获报错
3. 分析错误，修改代码
4. 写回文件，重新执行验证

---

**场景 4：操作另一台服务器**

> "切换到 server2，跑一下 nvidia-smi 看看 GPU 状态"

Claude 会在 server2 上新建 Kernel 并执行，与 server1 的 Kernel 完全独立。

---

**场景 5：限定本对话只访问某台服务器**

> "这个窗口只允许操作 server1，帮我设置一下"

Claude 会执行 `session set server1`，此后本对话所有操作都限定在 server1。

---

### Kernel 复用机制

Claude 会自动管理 Kernel 生命周期，无需手动干预：

```
你说："跑一下这段代码"
  → Claude 检查是否有已保存的 Kernel（按服务器隔离）
  → 有：直接复用（变量/导入状态保持）
  → 没有：自动新建并保存

你说："再跑下一步"
  → Claude 自动用同一个 Kernel，上一步的变量还在
```

---

## 命令参考（手动调用）

如果需要手动调用，所有命令在 `jupyter_tools/` 目录下执行：

### 全局 `--server` 参数

所有命令均支持 `--server <ID>` 指定目标服务器，不填则使用 `config.ini` 中的默认服务器：

```bash
python cli.py --server server2 execute --code "print('hello')"
python cli.py --server server2 kernel list
```

### 服务器管理

```bash
python cli.py server list                                             # 列出所有服务器
python cli.py server add --id server2 --host 10.0.0.1 --port 8888 --token xxx --name "训练机B"
python cli.py server remove --id server2                             # 删除服务器
python cli.py server default --id server2                            # 设置默认服务器
```

### Session 范围管理

每个对话窗口可独立限定可访问的服务器（写入 `.session_servers` 文件）：

```bash
python cli.py session set server1 server2   # 本 session 只允许访问 server1/server2
python cli.py session list                  # 查看当前 session 范围
python cli.py session clear                 # 清除限制（恢复访问所有服务器）
```

### 执行代码

```bash
python cli.py execute --code "print(1 + 1)"
python cli.py execute --file /path/to/script.py
python cli.py execute --kernel new --code "..."     # 强制新建 Kernel
python cli.py execute --code "..." --timeout 300    # 自定义超时
python cli.py execute --code "..." --save report.md # 保存结果
```

### Kernel 管理

```bash
python cli.py kernel list                  # 列出所有 Kernel
python cli.py kernel current               # 查看当前保存的 Kernel ID
python cli.py kernel restart --id <ID>     # 重启（清空变量）
python cli.py kernel delete  --id <ID>     # 删除
python cli.py kernel clear                 # 清除保存的 Kernel ID
```

### Notebook 操作

```bash
python cli.py notebook list                                        # 列出 Notebook
python cli.py notebook get-code --path work/analysis.ipynb        # 提取所有代码
python cli.py notebook append   --path work/analysis.ipynb --code "df.head()"
python cli.py notebook create   --path work/new.ipynb
```

### 远程文件操作

```bash
python cli.py file list   --path some/dir
python cli.py file read   --path data/script.py
python cli.py file write  --path data/script.py --content "print('hi')"
python cli.py file delete --path data/old.py
```

### 权限管理

```bash
python cli.py permissions          # 查看当前权限配置
```

写入、删除操作会自动校验权限，违规时直接报错：

```
❌ 删除操作已被禁用（allow_delete = false）
   如需开启，请修改 config.ini 中的 allow_delete = true

❌ 路径不在允许范围内: /outside/path
   允许的目录: /mnt/your/work/dir

❌ 服务器 'server3' 不在本 session 的允许列表中
   允许的服务器: server1, server2
```

**权限规则优先级：**
1. `allowed_dirs` 为空 → 不限制路径
2. `allow_delete = false` → 所有删除操作被拦截
3. `protected_dirs` → 即使 `allow_delete = true`，保护目录下也禁止删除
4. `.session_servers` 存在 → 只允许访问其中列出的服务器
