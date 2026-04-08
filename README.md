# JupyterTool

让 Claude Code 直接操作远程 Jupyter 服务器——执行代码、管理 Kernel、读写文件、调试脚本，全程用自然语言驱动。

## 项目结构

```
jupyterTool/
├── config.ini              # 服务器配置（host / port / token）
├── jupyter_tools/          # 核心工具代码
│   ├── config.py           # 读取 config.ini
│   ├── kernel.py           # Kernel 管理 + 状态持久化
│   ├── execute.py          # 代码执行（WebSocket）
│   ├── notebook.py         # Notebook & 远程文件操作
│   ├── file.py             # 本地结果保存
│   ├── cli.py              # 命令行入口
│   └── .kernel_state.json  # 自动生成，记录当前 Kernel ID
└── skill/
    └── SKILL.md            # Claude Code Skill 定义
```

## 配置

编辑项目根目录的 `config.ini`：

```ini
[jupyter]
host = 33.32.31.46
port = 8420
token = your-jupyter-token
```

## Vibe Coding 教程

> 配置好之后，你不需要记任何命令。直接用中文告诉 Claude 你想做什么，它会自动调用工具完成。

### 第一步：安装 Skill

将 `skill/SKILL.md` 安装到 Claude Code：

```bash
cp -r skill/  ~/.claude/skills/jupyter-notebook/
```

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

**场景 4：查看服务器文件**

> "查看一下 /mnt/data/ 下有哪些文件"

Claude 会在 Kernel 里执行 `os.listdir()` 返回文件列表。

---

**场景 5：管理 Kernel**

> "把当前 Kernel 重启一下，清空变量"
> "看看现在有几个 Kernel 在跑"
> "把没用的 Kernel 都删掉"

---

### Kernel 复用机制

Claude 会自动管理 Kernel 生命周期，无需手动干预：

```
你说："跑一下这段代码"
  → Claude 检查是否有已保存的 Kernel
  → 有：直接复用（变量/导入状态保持）
  → 没有：自动新建并保存

你说："再跑下一步"
  → Claude 自动用同一个 Kernel，上一步的变量还在
```

---

## 命令参考（手动调用）

如果需要手动调用，所有命令在 `jupyter_tools/` 目录下执行：

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
