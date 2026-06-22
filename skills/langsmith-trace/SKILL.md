---
name: langsmith-trace
description: LangSmith Trace 排障与观测。覆盖 CLI 安装、自动 Trace 采集、5 步排障工作流、Trace 树结构解读。当用户需要调试 Agent 行为、添加 Tracing、排查慢 Trace、或问 LangSmith 相关问题时激活。触发词：langsmith、trace、tracing、debug agent、add tracing、set up tracing、LangSmith、慢请求、慢调用。
---

# LangSmith Trace 排障指南

> LangSmith 是 LangChain 生态的**全生命周期观测平台**。本 skill 负责 **「怎么查」**——Trace 采集、CLI 排障、命令速查。
> 写代码 → `/langchain-v1` | 自定义图 → `/langgraph-v1` | 电池包 → `/deepagents-v1` | 选型 → `/agent-sdk-router`

## ⚠️ 安全警告

**绝对不要用 `--api-key` CLI 标志传递 API Key！** CLI 自动从环境变量读取 `LANGSMITH_API_KEY`。使用 `--api-key <value>` 会把密钥泄露到 shell 历史、进程列表、agent tool-call 日志中。

---

## 1. 安装与配置

### 安装 CLI

```bash
curl -sSL https://raw.githubusercontent.com/langchain-ai/langsmith-cli/main/scripts/install.sh | sh
```

二进制安装到 `~/.local/bin/langsmith`。找不到命令时：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

### 设置 API Key

```bash
# .env 或 ~/.zshrc 中
export LANGSMITH_API_KEY=<your-key-here>  # 以 lsv2_pt_ 开头
```

获取 Key：https://smith.langchain.com/settings

### 验证

```bash
langsmith project list
```

返回 JSON 数组即成功。常见失败：
- **`command not found`** — `~/.local/bin` 不在 PATH
- **401 Unauthorized** — key 过期或错误
- **空数组 `[]`** — 认证成功但还没 project，去 UI 创建或跑一个 traced app

---

## 2. 添加 Trace

### LangGraph / LangChain App（自动采集）

无需改代码，设环境变量即可：

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-key-here>
export LANGSMITH_PROJECT=my-project  # 可选，默认 "default"
```

Serverless（Python）额外设置：

```bash
export LANGCHAIN_CALLBACKS_BACKGROUND=false  # 确保 trace 在函数退出前 flush
```

### 非 LangChain App

用 `@traceable` 装饰器 + `wrap_openai`：

```python
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import OpenAI

client = wrap_openai(OpenAI())

@traceable
def my_pipeline(question: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}],
    )
    return resp.choices[0].message.content
```

---

## 3. 5 步排障工作流

这是排查 Agent 行为的推荐流程：

### Step 1：找到正确的 Project

```bash
langsmith project list
```

查看 `last_run_start_time` 确定哪个 project 有最近活动。**注意**：LangGraph app 默认 trace 到 `"default"` project。

### Step 2：列出最近的 Trace

```bash
langsmith trace list --project default --limit 5
# 带层级结构（合并 Step 2+3）
langsmith trace list --project default --limit 5 --show-hierarchy
```

### Step 3：获取 Trace 层级

```bash
langsmith trace get <trace-id> --project <name>
```

返回完整 run tree — 理解 Agent 执行流程的核心命令。

### Step 4：获取所有 Run 的 IO

```bash
langsmith run list --trace-ids <trace-id> --project <name> --include-io
```

每个 run（LLM 调用、tool 调用、middleware）的 inputs/outputs。

### Step 5：深入具体 Run

```bash
langsmith run get <run-id> --include-io
```

---

## 4. Trace 树结构解读

LangGraph Agent 的典型 trace 层级：

```
<agent_name> (root chain)
├── SkillsMiddleware.before_agent
├── MemoryMiddleware.before_agent
├── model (chain) ← LLM 回合
│   ├── TodoListMiddleware.awrap_model_call
│   ├── SkillsMiddleware.awrap_model_call
│   ├── FilesystemMiddleware.awrap_model_call
│   ├── SubAgentMiddleware.awrap_model_call
│   ├── SummarizationMiddleware.awrap_model_call
│   ├── MemoryMiddleware.awrap_model_call
│   └── ChatOpenAI (llm) ← 真正的 LLM 调用（inputs/outputs 在这层）
├── tools (chain) ← 工具执行
│   ├── FilesystemMiddleware.awrap_tool_call
│   └── <tool_name> (tool) ← 真正的工具（inputs/outputs 在这层）
├── model (chain) ← 下一轮 LLM
│   └── ... (相同 middleware 栈)
```

**关键理解**：
- **真正的 LLM 调用**是最内层的 `ChatOpenAI` run
- **工具结果**在 `<tool_name>` run 中
- Middleware wrappers 是透明的 — 你关心的 IO 在叶子节点

---

## 5. 踩坑记录

### `--full` vs `--include-io`

**问题**：`langsmith run get <id> --full` 可能返回 null IO。

**修复**：

```bash
# ✅ 永远用这个
langsmith run get <run-id> --include-io
# ❌ 可能返回 null
langsmith run get <run-id> --full
```

### IO 始终为 null

检查 `.env` 中是否关闭了 IO 采集：

```bash
LANGCHAIN_HIDE_INPUTS=true    # 隐藏 inputs → 改为 false
LANGCHAIN_HIDE_OUTPUTS=true   # 隐藏 outputs → 改为 false
```

### Project 找不到 Trace

LangGraph app 默认 trace 到 `"default"` project。先 `langsmith project list` 确认 `last_run_start_time`。

---

## 6. 实用命令速查

```bash
# 基础
langsmith project list                                            # 列 project
langsmith trace list --project default --limit 10                  # 最近 trace
langsmith trace list --project default --error --last-n-minutes 60 # 失败的
langsmith trace list --project default --min-latency 5.0           # 慢的 (>5s)

# Trace 树
langsmith trace get <trace-id> --project default                   # 完整层级

# Run IO
langsmith run list --trace-ids <id> --project default --include-io # 全部 run+IO
langsmith run list --trace-ids <id> --run-type llm --include-io    # 只看 LLM
langsmith run list --trace-ids <id> --run-type tool --include-io   # 只看工具
langsmith run get <run-id> --include-io                            # 单个 run 详情

# 导出
langsmith trace export ./traces --project default --limit 20 --full
```

### Traces vs Runs

| | `trace *` | `run *` |
|---|---|---|
| 返回 | 完整层级（树） | 平面列表 |
| `--run-type` | 不可用 | 可用（llm, chain, tool, retriever） |
| 导出 | 目录（每个 trace 一个文件） | 单 JSONL 文件 |
| 何时用 | **先看这个** — 全局视角 | 深入特定 run 类型 |

> 完整 CLI 命令树 → `reference/cli-commands.md`

---

> **返回**: 写代码 → `/langchain-v1` | 自定义图 → `/langgraph-v1` | 电池包 → `/deepagents-v1`
