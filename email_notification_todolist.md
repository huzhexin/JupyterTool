# 邮件通知系统 Todolist

## 背景分析

当前异步任务完成后，只会更新 `.task_state.json` 的状态，没有主动通知机制。
用户需要主动轮询 `task status` 才能知道任务结束，对于跑半小时以上的任务体验较差。

**目标**：任务完成（或失败）后，自动发送邮件通知，告知状态、耗时、输出摘要。
**可选性**：`config.ini` 中不配置 `[email]` 节，则完全不发邮件，不影响现有功能。

---

## 架构设计

### 触发点

邮件发送在 `worker.py` 的 `finish_task()` 调用之后触发，这是任务完成的唯一收口：

```
worker.py::run()
    └── finish_task(task_id, output, error)   ← 更新状态
    └── send_task_email(task_id, output, error)  ← 新增：发邮件（若已配置）
```

### config.ini 新增 `[email]` 节

```ini
[email]
# 是否启用邮件通知（true/false，不填或 false 则禁用）
enabled = true

# SMTP 服务器配置
smtp_host = smtp.example.com
smtp_port = 465
smtp_user = your@email.com
smtp_password = your_password

# 收件人（逗号分隔，支持多人）
to = your@email.com, teammate@email.com

# 可选：发件人名称（默认用 smtp_user）
from_name = JupyterTool 通知

# 可选：只在任务失败时发邮件（true/false，默认 false = 成功失败都发）
only_on_error = false
```

### 邮件内容

- **主题**：`[JupyterTool] ✅ 任务完成: <code_snippet>` 或 `[JupyterTool] ❌ 任务失败: <code_snippet>`
- **正文**：
  - 任务 ID、服务器、提交时间、完成时间、耗时
  - 输出摘要（前 2000 字符，超出提示查看日志）
  - 错误信息（如有）

---

## TODO 列表

### Phase 1：邮件发送核心模块

- [x] **1.1 新建 `jupyter_tools/notifier.py`**
  - `load_email_config()` 从 `config.ini` 读取 `[email]` 节，返回配置 dict 或 `None`（未配置/禁用时）
  - `send_email(subject, body, cfg)` 通过 `smtplib` 发送邮件
    - 支持 SSL（端口 465）和 STARTTLS（端口 587）自动判断
    - 使用标准库 `smtplib` + `email.mime`，无额外依赖
  - `send_task_notification(task_id, output, error)` 组装任务完成邮件并发送
    - 读取 `config.ini` 判断是否启用
    - 读取 `.task_state.json` 获取任务元信息（提交时间、服务器、代码摘要等）
    - 计算耗时
    - 组装主题和正文
    - 调用 `send_email()`
    - 发送失败时打印警告，不抛异常（不影响主流程）
  - 新建文件：`jupyter_tools/notifier.py`

### Phase 2：集成到 worker.py

- [x] **2.1 在 `worker.py::run()` 末尾调用邮件通知**
  - `finish_task()` 之后，调用 `send_task_notification(task_id, output, error)`
  - 用 `try/except` 包裹，邮件失败不影响任务状态写入
  - 修改文件：`jupyter_tools/worker.py`

### Phase 3：config.ini 更新

- [x] **3.1 在 `config.ini` 中添加 `[email]` 节示例（注释掉）**
  - 提供完整的配置示例，方便用户直接取消注释使用
  - 包含国内常用邮箱（QQ、163、企业邮箱）的 SMTP 参数说明
  - 修改文件：`config.ini`

### Phase 4：CLI 支持（可选，方便测试）

- [x] **4.1 新增 `python cli.py email test` 命令**
  - 读取 `[email]` 配置，发一封测试邮件，验证配置是否正确
  - 输出：`✅ 测试邮件已发送` 或具体错误信息
  - 修改文件：`cli.py`

### Phase 5：SKILL.md 更新

- [x] **5.1 补充邮件通知配置说明**
  - 在 SKILL.md 中说明如何配置邮件
  - 说明 `email test` 命令用法
  - 修改文件：`skill/SKILL.md`

---

## 文件改动汇总

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `jupyter_tools/notifier.py` | 新建 | 邮件发送核心模块 |
| `jupyter_tools/worker.py` | 修改 | 任务完成后调用邮件通知 |
| `jupyter_tools/cli.py` | 修改 | 新增 `email test` 命令 |
| `config.ini` | 修改 | 新增 `[email]` 节示例（注释形式） |
| `skill/SKILL.md` | 修改 | 补充邮件配置说明 |

---

## 关键设计决策

**1. 完全可选，零侵入**
- `[email]` 节不存在 或 `enabled = false` → 完全跳过，现有行为不变
- 不引入任何新的第三方依赖（只用标准库 `smtplib`）

**2. 失败静默**
- 邮件发送失败（网络问题、密码错误等）只打印警告到 worker 日志，不抛异常
- 任务状态已经正确写入 `.task_state.json`，邮件只是额外通知

**3. 触发时机**
- 只在 `worker.py` 的异步任务完成时发邮件
- 同步执行（不带 `--async`）不发邮件（同步任务 Claude 本身就在等结果）

**4. `only_on_error` 选项**
- 跑训练时可能只关心失败的情况，成功了自然会去看结果
- 设置 `only_on_error = true` 后，只有任务失败才发邮件

---

## 优先级建议

**Phase 1 + 2 + 3 是核心**，实现后即可使用邮件通知。
**Phase 4**（`email test` 命令）强烈建议做，配置 SMTP 参数容易出错，测试命令能大幅降低调试成本。
**Phase 5** 随手更新即可。
