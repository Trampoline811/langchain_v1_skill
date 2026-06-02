---
name: deepagents-v1
description: Deep Agents 开箱即用 agent harness 代码生成规范。内置文件系统、子agent、规划、上下文管理、代码执行。当用户需要复杂多步任务、代码生成/执行、深度研究、内容构建等完整 agent 堆栈时使用。触发词：deepagents、create_deep_agent、sandbox、代码执行、filesystem、文件系统、长任务、subagent 集群、深度研究、内容构建、FilesystemMiddleware、SubAgentMiddleware、SkillsMiddleware、MemoryMiddleware。
---

# Deep Agents v1 编码规范

> Deep Agents = `create_agent()` + **预组装中间件堆栈**。内置文件系统、摘要、子 agent、记忆、技能。
> `create_deep_agent()` 开箱即用；需要精细控制时用 `create_agent()` + 手选中间件。

## 定位

```
DeepAgents  ← 预组装 harness ← 你现在在这
    │         内置: FilesystemMiddleware + SummarizationMiddleware
    │         + SubAgentMiddleware + MemoryMiddleware + SkillsMiddleware
    │         适用: 长任务、代码生成、深度研究、内容构建
    │
LangChain   ← Agent框架 (create_agent, @tool, middleware)
    │
LangGraph   ← 编排运行时 (StateGraph, persistence, streaming)
```

---

## 1. 快速开始

```python
# pip install deepagents langchain-openai
from deepagents import create_deep_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="You are a helpful assistant.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in SF?"}]}
)
```

**`create_deep_agent()` 自动装配：**
- `FilesystemMiddleware` — 虚拟文件系统，读写文件跨轮次保留
- `SummarizationMiddleware` — 上下文超限自动压缩
- `SubAgentMiddleware` — 内置 `general-purpose` 子 agent
- `MemoryMiddleware` — 从 `AGENTS.md` 加载持久记忆
- `SkillsMiddleware` — 从 `skills/` 目录加载领域知识

---

## 2. 内置能力

### 2.1 文件系统（FilesystemMiddleware）

```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    backend=StateBackend(),  # 或 FilesystemBackend(root_dir="...")
)

# Agent 自动获得文件系统工具：read_file, write_file, edit_file, ls, glob, grep
# 文件跨轮次持久化在 state 中
```

**StateBackend vs FilesystemBackend:**
| Backend | 存储位置 | 适用 |
|---------|---------|------|
| `StateBackend()` | Agent state（内存） | 临时文件、单次任务 |
| `FilesystemBackend(root_dir)` | 磁盘目录 | 持久文件、跨会话 |

### 2.2 代码执行（Interpreters + Sandboxes）

```python
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    middleware=[
        FilesystemMiddleware(backend=StateBackend()),
        # 内置 Python 解释器 — agent 可以执行代码
    ],
)
# Agent 拥有 execute_python 工具，可运行任意代码
```

**Sandboxes 隔离级别：**
- 本地进程（默认）— 最快，无额外依赖
- Docker sandbox — 完全隔离，需 Docker
- 远程 sandbox — 通过 `remote-sandboxes` 配置

### 2.3 子 Agent（SubAgentMiddleware）

```python
from deepagents import create_deep_agent, SubAgent
from deepagents.middleware import SubAgentMiddleware
from deepagents.backends import StateBackend

researcher: SubAgent = {
    "name": "researcher",
    "description": "Searches web and returns structured summaries",
    "tools": [web_search],
    "model": "claude-sonnet-4-6",       # 子 agent 专属模型
    "system_prompt": "You are a thorough researcher.",
}

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[web_search],
    middleware=[
        SubAgentMiddleware(
            default_model="claude-haiku-4-5",
            subagents=[researcher],
            backend=StateBackend(),
        ),
    ],
)
# 主 agent 自动调用 researcher 子 agent，子 agent 在独立上下文中运行
```

**子 Agent 三种形态：**
| 形态 | 用法 |
|------|------|
| Dict 定义 | `{"name": "...", "tools": [...], "description": "..."}` |
| 预编译 Graph | `CompiledSubAgent(name="...", runnable=graph)` |
| create_deep_agent 转子 | `create_deep_agent(name="...", ...).as_subagent()` |

### 2.4 记忆（MemoryMiddleware）

```python
from deepagents.middleware import MemoryMiddleware

MemoryMiddleware(
    backend=StateBackend(),
    sources=["./AGENTS.md"],  # 项目级指令，Agent 启动时自动加载
)
# 记忆跨会话持久化，写入 store 后下次自动可用
```

### 2.5 技能（SkillsMiddleware）

```python
from deepagents.middleware import SkillsMiddleware

SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],  # 技能目录，按需加载
)
# Agent 遇到相关任务时加载对应 skill，而非全部预载入上下文
```

---

## 3. 上下文工程（Context Engineering）

Deep Agents 的核心优势：**自动管理上下文窗口**。

```python
from deepagents.backends import StateBackend
from deepagents.middleware import (
    FilesystemMiddleware,
    SummarizationMiddleware,
    MemoryMiddleware,
    SkillsMiddleware,
)

backend = StateBackend()
model = "claude-sonnet-4-6"

agent = create_deep_agent(
    model=model,
    tools=[search],
    backend=backend,
    middleware=[
        FilesystemMiddleware(backend=backend),
        SummarizationMiddleware(
            model=model,                    # 摘要用同一模型
            backend=backend,
            trigger=("tokens", 100000),      # 超 100K tokens 触发压缩
            keep=("messages", 20),           # 保留最近 20 条消息
        ),
        MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
        SkillsMiddleware(backend=backend, sources=["./skills/"]),
    ],
)
```

---

## 4. 权限控制

```python
from deepagents.middleware.permissions import PermissionsMiddleware

PermissionsMiddleware(
    allowed_tools=["read_file", "search"],   # 白名单
    denied_tools=["delete_file", "execute_shell"],  # 黑名单
    allowed_paths=["/workspace/"],           # 文件系统路径限制
)
```

---

## 5. Human-in-the-Loop

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[write_file, execute_code],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={
            "write_file": True,
            "execute_code": {"allowed_decisions": ["approve", "reject"]},
        }),
    ],
)
```

---

## 6. 生产部署

```python
# 1. 用 FilesystemBackend 替代 StateBackend
from deepagents.backends import FilesystemBackend
backend = FilesystemBackend(root_dir="./agent_workspace")

# 2. 用 PostgresSaver + PostgresStore 持久化
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

# 3. 部署到 LangSmith
# LangSmith 自动配置 checkpointer + store

# 4. 配置 profiles（模型能力精细化控制）
from deepagents.profiles import CodeAgentProfile
agent = create_deep_agent(
    model="claude-sonnet-4-6",
    profile=CodeAgentProfile(),  # 预设代码场景最佳参数
)
```

---

## 7. create_deep_agent() vs create_agent() 决策

| 场景 | create_agent() | create_deep_agent() |
|------|:--:|:--:|
| 简单 tool-calling | ✅ | ❌ 过重 |
| 需要写文件/跨轮次状态 | ❌ | ✅ |
| 需要自动上下文压缩 | ❌ | ✅ |
| 需要子 agent 并行 | ❌ | ✅ |
| 需要代码执行沙箱 | ❌ | ✅ |
| 需要权限控制 | ❌ | ✅ |
| 需要最小依赖 | ✅ | ❌ |

---

## 8. 执行协议

1. **简单任务用 `create_agent()`** — 不要上来就 deepagents
2. **需要上下文管理 → `create_deep_agent()`** — 自动压缩 + 文件系统
3. **需要子 agent 并行 → 加 `SubAgentMiddleware`** — 每个子 agent 独立上下文
4. **生产环境用 FilesystemBackend** — StateBackend 不持久化
5. **微调中间件 → `create_agent()` + 手选 middleware** — 精确控制堆栈
