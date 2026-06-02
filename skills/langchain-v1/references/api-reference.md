# LangChain v1 API 完整参考

> 按需查阅。日常编码只需 SKILL.md 的速查表。

## 中间件完整目录

### 内置中间件（Python）

导入路径前缀: `from langchain.agents.middleware import *`

| 中间件 | 用途 | 关键参数 |
|--------|------|---------|
| `HumanInTheLoopMiddleware` | 敏感操作需审批 | `interrupt_on={"tool": True \| {"allowed_decisions": ["approve","edit","reject"]}}` |
| `ToolRetryMiddleware` | 工具调用自动重试 | `max_retries=2, retry_on=(Exception,), backoff_factor=2.0, initial_delay=1.0, max_delay=60.0, jitter=True, on_failure="return_message"` |
| `ModelRetryMiddleware` | 模型调用自动重试 | `max_retries=2, retry_on=(Exception,), on_failure="continue"` |
| `SummarizationMiddleware` | 长对话自动摘要 | `model` (必填), `trigger=("tokens", 8000) \| ("messages", 20) \| ("fraction", 0.8)`, `keep=("messages", 20)`, `token_counter`, `summary_prompt` |
| `PIIMiddleware` | 敏感信息检测/脱敏 | `pii_type` (str), `strategy="redact" \| "block" \| "mask" \| "hash"`, `detector=None`, `apply_to_input=True`, `apply_to_output=False` |
| `ModelFallbackMiddleware` | 模型降级链 | `*models: str \| BaseChatModel` (变长参数，fallback 链) |
| `TodoListMiddleware` | 任务规划跟踪 | `system_prompt`, `tool_description` |
| `ModelCallLimitMiddleware` | 限制模型调用次数 | `thread_limit`, `run_limit`, `exit_behavior="end" \| "error"` |
| `ToolCallLimitMiddleware` | 限制工具调用次数 | `tool_name`, `thread_limit`, `run_limit`, `exit_behavior="continue" \| "error" \| "end"` |
| `ContextEditingMiddleware` | 清理旧 tool 结果 | `edits=[ClearToolUsesEdit(trigger=100000, keep=3)]` |
| `LLMToolSelectorMiddleware` | LLM 动态选择工具子集 | `model`, `system_prompt`, `max_tools`, `always_include` |
| `LLMToolEmulator` | 用 LLM 模拟工具调用 | `tools=None`, `model=None` |
| `ShellToolMiddleware` | 提供 shell 执行环境 | `workspace_root`, `startup_commands`, `execution_policy` |
| `FilesystemFileSearchMiddleware` | 文件系统搜索工具 | `root_path`, `use_ripgrep=True`, `max_file_size_mb=10` |

### DeepAgents 中间件（需安装 deepagents）

| 中间件 | 用途 | 导入路径 |
|--------|------|---------|
| `FilesystemMiddleware` | 虚拟文件系统 | `deepagents.middleware.filesystem` |
| `SubAgentMiddleware` | 子 Agent 管理 | `deepagents.middleware.subagents` |
| `MemoryMiddleware` | 持久记忆加载 | `deepagents.middleware` |
| `SkillsMiddleware` | 领域知识注入 | `deepagents.middleware` |

### 中间件示例

**HumanInTheLoopMiddleware:**
```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

agent = create_agent("openai:gpt-5.4", tools=[send_email, delete_record],
    checkpointer=InMemorySaver(),  # HITL 必须！
    middleware=[HumanInTheLoopMiddleware(interrupt_on={
        "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
        "delete_record": True,
    })])
result = agent.invoke({"messages": [...]}, config={"configurable": {"thread_id": "t1"}})
# 审批: agent.invoke(Command(resume={"type": "approve"}), config={"configurable": {"thread_id": "t1"}})
```

**SummarizationMiddleware:**
```python
from langchain.agents.middleware import SummarizationMiddleware

SummarizationMiddleware(
    model="openai:gpt-5-nano",       # 摘要用便宜模型
    trigger=("tokens", 100000),        # 超过 100K tokens 触发
    keep=("messages", 20),             # 保留最近 20 条消息
)
```

**ContextEditingMiddleware + ClearToolUsesEdit:**
```python
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit

ContextEditingMiddleware(edits=[
    ClearToolUsesEdit(
        trigger=100000,        # token 阈值
        clear_at_least=0,      # 最少回收 token
        keep=3,                # 保留最近 N 个 tool 结果
        exclude_tools=[],      # 排除特定工具
        placeholder="[cleared]",
    )
])
```

**ToolRetryMiddleware:**
```python
ToolRetryMiddleware(
    max_retries=3,
    backoff_factor=2.0,
    initial_delay=1.0,
    max_delay=60.0,
    jitter=True,
    tools=["api_tool"],   # None = 所有工具
    retry_on=(ConnectionError, TimeoutError),
    on_failure="return_message",  # 或 "raise" 或 Callable
)
```

**ModelFallbackMiddleware:**
```python
from langchain.agents.middleware import ModelFallbackMiddleware

ModelFallbackMiddleware(
    "claude-sonnet-4-6",           # 主模型
    "openai:gpt-5.4",              # 第一个 fallback
    "google_genai:gemini-2.5-flash", # 第二个 fallback
)
```

**PIIMiddleware:**
```python
from langchain.agents.middleware import PIIMiddleware

PIIMiddleware(
    pii_type="email",
    strategy="redact",        # 或 "block", "mask", "hash"
    apply_to_input=True,
    apply_to_output=True,
    apply_to_tool_results=True,
)
```

---

## 自定义中间件

### 钩子装饰器

```python
from langchain.agents.middleware import (
    before_model, after_model, after_agent,
    wrap_model_call, dynamic_prompt
)

@before_model
def inject_context(state, runtime) -> dict | None:
    """模型调用前执行。返回 dict 可更新 state，返回 None 跳过。"""
    user_id = runtime.context.user_id if runtime.context else "unknown"
    return {"system_prompt": f"Current user: {user_id}"}

@after_model
def audit_response(state, runtime) -> None:
    """模型返回后执行。用于日志、审计。"""
    last = state["messages"][-1]
    logger.info(f"Model used {last.usage_metadata}")

@after_agent
def final_validation(state, runtime) -> dict | None:
    """Agent 结束时执行。可修改最终 state。"""
    if "PII" in str(state["messages"]):
        return {"messages": [AIMessage(content="Response blocked: PII detected")]}

@dynamic_prompt
def adaptive_prompt(state, runtime) -> str | None:
    """动态注入系统提示。每次模型调用都会执行。"""
    return f"Current time: {datetime.now()}"  # 返回新提示追加到 system prompt

@wrap_model_call
def model_router(request, handler):
    """包裹模型调用。可修改 request 或 response。"""
    if len(request.state["messages"]) > 20:
        request = request.override(model="claude-sonnet-4-6")  # 切换模型
    return handler(request)
```

### 中间件类（跨钩子共享状态）

```python
from langchain.agents.middleware import AgentMiddleware

class RateLimitMiddleware(AgentMiddleware):
    def __init__(self, max_calls=10):
        super().__init__()
        self.max_calls = max_calls
        self.count = 0

    def before_model(self, state, runtime):
        self.count += 1
        if self.count > self.max_calls:
            raise RuntimeError(f"Exceeded {self.max_calls} model calls")
```

---

## ToolRuntime 完整参考

```python
from langchain.tools import ToolRuntime

class ToolRuntime:
    state: dict              # 短期记忆：当前对话的完整 state
    context: Any             # 不可变运行时数据（由 context_schema 定义）
    store: BaseStore         # 长期记忆：跨对话持久化存储
    stream_writer: callable  # 工具内发送实时更新
    tool_call_id: str        # 当前工具调用的唯一 ID
    config: RunnableConfig   # callbacks, tags, metadata, thread_id
    execution_info: object   # thread_id, run_id, node_attempt
```

### Command — 工具返回写状态

```python
from langgraph.types import Command
from langchain.messages import ToolMessage

@tool
def save_and_continue(data: str, runtime: ToolRuntime) -> Command:
    return Command(update={
        "custom_field": data,
        "messages": [ToolMessage(f"Saved: {data}", tool_call_id=runtime.tool_call_id)],
    })
```

---

## 结构化输出

### ProviderStrategy vs ToolStrategy

```python
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy

# ProviderStrategy — 模型原生支持（OpenAI, Anthropic, xAI, Gemini）
# 最高可靠性，provider 端强制 schema
ProviderStrategy(schema=PydanticModel, strict=False)  # strict 需 langchain>=1.2

# ToolStrategy — 兼容所有模型，通过 tool calling 实现
ToolStrategy(
    schema=PydanticModel,
    tool_message_content="Custom message",  # 可选自定义
    handle_errors=True,                     # 默认自动重试
    # handle_errors 可选值: False | str | type[Exception] | tuple | Callable
)

# 直接传 schema → 自动选择策略
agent = create_agent(model=..., response_format=MyPydanticModel)
```

---

## 流式输出

### v2 格式 (agent.stream)

```python
for mode, chunk in agent.stream(
    {"messages": [...]}, config=config,
    stream_mode=["messages", "updates", "custom", "values", "events"],
    version="v2",
):
    if mode == "messages":
        msg_chunk, metadata = chunk
```

### v3 格式 (agent.stream_events) — 推荐新项目

```python
for event in agent.stream_events(
    {"messages": [...]}, config=config, version="v3",
):
    event["text"]         # str — 文本增量
    event["reasoning"]    # list[dict] — 思考过程
    event["tool_calls"]   # list[dict] — 工具调用
    event["output"]       # dict — 最终结构化输出
    event["subgraphs"]    # 子 agent 的流式事件（需 subgraphs=True）
```

---

## 检查点方案

```python
# 开发
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver()

# 本地持久化
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# 生产 — PostgreSQL
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string("postgresql://...")

# 生产 — LangSmith 部署时自动配置，无需手动传
```

---

## 长期记忆 (store)

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
agent = create_agent(model, tools=[...], store=store)

# 工具内读写
@tool
def save_info(key: str, value: str, runtime: ToolRuntime) -> str:
    runtime.store.put(("namespace",), key, {"data": value})
    return "Saved"

@tool  
def load_info(key: str, runtime: ToolRuntime) -> str:
    item = runtime.store.get(("namespace",), key)
    return str(item.value) if item else "Not found"

# 生产：PostgresStore
```

---

## 多智能体 — 五种模式

| 模式 | 分布式 | 并行 | 多跳 | 用户交互 | 模型调用 | 最佳场景 |
|------|:--:|:--:|:--:|:--:|:--:|------|
| Subagents | ⭐5 | ⭐5 | ⭐5 | ⭐ | 4 | 并行处理、复杂研究 |
| Handoffs | - | - | ⭐5 | ⭐5 | 3 | 客服转接 |
| Skills | ⭐5 | ⭐3 | ⭐5 | ⭐5 | 3 | SQL 助手、领域知识 |
| Router | ⭐3 | ⭐5 | - | ⭐3 | 3 | 简单分类 |
| Custom Workflow | ⭐5 | ⭐5 | ⭐5 | ⭐5 | 变 | 复合定制流程 |

### Subagents 模式

```python
from deepagents.middleware import SubAgentMiddleware

researcher = {
    "name": "researcher",
    "description": "Searches and returns structured summaries",
    "tools": [search],
    "model": "claude-sonnet-4-6",     # 可选：子 agent 专属模型
    "system_prompt": "You are a research assistant.",
}

agent = create_agent(model, tools=[search],
    middleware=[SubAgentMiddleware(
        default_model="claude-haiku-4-5",
        subagents=[researcher],
    )])
```

---

## 包结构速查

```
langchain (v1)
├── agents              → create_agent
├── agents.middleware   → 内置中间件
├── agents.structured_output → ToolStrategy, ProviderStrategy
├── chat_models         → init_chat_model
├── tools               → @tool, ToolRuntime
├── messages            → AIMessage, HumanMessage, ToolMessage

langgraph (独立包)
├── graph               → StateGraph, START, END
├── func                → @entrypoint, @task
├── checkpoint          → InMemorySaver, SqliteSaver, PostgresSaver
├── checkpoint.memory   → InMemorySaver
├── store.memory        → InMemoryStore
├── types               → Command, GraphInterrupt

langchain-classic (legacy)
└── chains, retrievers, indexes, embeddings ...
```
