---
name: langchain-v1
description: LangChain v1.0 (2025.11+) 代码生成规范。强制使用 create_agent/init_chat_model/@tool/middleware/checkpointer/store，禁用旧版 LLMChain/ChatOpenAI/AgentExecutor/ConversationBufferMemory。当用户写LangChain代码时激活。触发词：langchain、agent、create_agent、init_chat_model、@tool、middleware、checkpointer、ToolRuntime、structured output、streaming。
---

# LangChain v1.0 编码规范

> v1.0 只有四个概念：**model、agent、tool、middleware**。没有 chain。
> 本 skill 负责 **「怎么写」**。选型决策 → `references/decision-guide.md` | 完整 API → `references/api-reference.md` | 迁移 → `references/migration-comparison.md`

## 禁止使用（黑名单）

| ❌ 旧版 | ✅ v1.0 |
|----------|---------|
| `LLMChain` / `ConversationChain` | `create_agent()` |
| `ChatOpenAI(model="gpt-4")` | `init_chat_model("openai:gpt-4")` |
| `ChatAnthropic(model="...")` | `init_chat_model("claude-sonnet-4-6")` |
| `AgentExecutor` + `create_react_agent` | `create_agent()` |
| `ConversationBufferMemory()` | `checkpointer=InMemorySaver()` |
| `Tool.from_function(...)` | `@tool` 装饰器 |
| `InjectedState` / `InjectedStore` | `runtime: ToolRuntime` |
| `RunnableWithMessageHistory` | `create_agent()` + `checkpointer` |
| `create_csv_agent` / `create_pandas_dataframe_agent` | `create_agent()` + `@tool` |
| `from langchain.chains import ...` | `from langchain_classic.chains import ...` |
| `NodeInterrupt` | `GraphInterrupt` |
| `Command(goto=...)` | `Command(graph=...)` |

---

## 1. 快速开始

```python
# pip install langchain langchain-openai
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

agent = create_agent(
    model="openai:gpt-5.4",
    tools=[my_tool],
    system_prompt="You are a helpful assistant",
)
result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
```

---

## 2. create_agent() 完整签名

```python
from langchain.agents import create_agent

agent = create_agent(
    model: str | BaseChatModel,              # 必填. "provider:model" 或模型实例
    tools: list = [],                        # @tool 装饰的函数 / MCP 工具
    *,
    system_prompt: str | None = None,        # 静态系统提示词
    response_format: (                       # 结构化输出（见第6节）
        ToolStrategy | ProviderStrategy | type[BaseModel] | None
    ) = None,
    name: str | None = None,                 # 多 agent 系统中的节点名
    checkpointer: BaseCheckpointer | None = None,  # 对话持久化（InMemorySaver等）
    store: BaseStore | None = None,          # 长期记忆（InMemoryStore / PostgresStore）
    middleware: list = None,                  # 中间件列表（见第5节）
    context_schema: type | None = None,       # 每调用传入的不可变数据（dataclass/Pydantic）
    state_schema: type | None = None,         # 扩展 AgentState 的自定义字段
    # provider 专属参数:
    azure_deployment: str | None = None,      # Azure OpenAI 专用
    model_provider: str | None = None,        # Bedrock / HuggingFace 等
    temperature: float | None = None,
    max_tokens: int | None = None,
)
```

**model 格式**: `"provider:model_name"` — 如 `"openai:gpt-5.4"` / `"claude-sonnet-4-6"` / `"google_genai:gemini-2.5-flash"` / `"ollama:llama3.2"`

---

## 3. 模型初始化

```python
from langchain.chat_models import init_chat_model

# 基础
model = init_chat_model("claude-sonnet-4-6")
model = init_chat_model("openai:gpt-5.4", temperature=0.5, max_tokens=4096)

# 关键方法
model.invoke("prompt")                    # 同步调用
model.stream("prompt")                    # 流式
model.bind_tools([tool1, tool2])          # 绑定工具给模型
model.with_structured_output(Schema)      # 绑定结构化输出

# 速率限制
from langchain_core.rate_limiters import InMemoryRateLimiter
model = init_chat_model("gpt-5.4", rate_limiter=InMemoryRateLimiter(requests_per_second=0.1))
```

---

## 4. 工具定义

### 4.1 @tool 装饰器

```python
from langchain.tools import tool

@tool
def search(query: str, limit: int = 10) -> str:
    """Search database for records. Use when looking up user info."""
    return f"Found {limit} results for '{query}'"

# 自定义名称和描述
@tool("calculator", description="Performs arithmetic")
def calc(expr: str) -> str: ...

# Pydantic schema
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    location: str = Field(description="City name")
    units: str = Field(default="celsius")

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius") -> str: ...
```

### 4.2 ToolRuntime（访问运行时上下文）

```python
from langchain.tools import tool, ToolRuntime

@tool
def my_tool(query: str, runtime: ToolRuntime) -> str:
    # 短期记忆 — 当前对话状态
    msgs = runtime.state["messages"]
    user_name = runtime.state.get("user_name")

    # 长期记忆 — 跨对话持久化（namespace/key 模式）
    prefs = runtime.store.get(("users",), runtime.context.user_id)

    # 不可变配置 — 每次 invoke 时传入
    role = runtime.context.user_role

    # 工具调用 ID
    call_id = runtime.tool_call_id
    return ...
```

### 4.3 Command — 工具内写状态

```python
from langgraph.types import Command
from langchain.messages import ToolMessage

@tool
def set_user_name(name: str, runtime: ToolRuntime) -> Command:
    """Set the user's name in conversation state."""
    return Command(update={
        "user_name": name,
        "messages": [ToolMessage(f"Name set to {name}", tool_call_id=runtime.tool_call_id)],
    })
```

---

## 5. 中间件

### 5.1 内置中间件速查

| 中间件 | 用途 | 关键参数 |
|--------|------|---------|
| `HumanInTheLoopMiddleware` | 敏感操作需审批 | `interrupt_on={"tool_name": True}` |
| `ToolRetryMiddleware` | 工具失败自动重试 | `max_retries=3, backoff_factor=2.0` |
| `ModelRetryMiddleware` | 模型调用失败重试 | `max_retries=3` |
| `SummarizationMiddleware` | 长对话自动摘要 | `model=..., trigger=("tokens", 8000)` |
| `PIIMiddleware` | 敏感信息脱敏 | `pii_type="email", strategy="redact"` |
| `ModelFallbackMiddleware` | 模型降级链 | `ModelFallbackMiddleware(fast, slow, fallback)` |
| `TodoListMiddleware` | 复杂任务自动规划 | 无需配置 |
| `ModelCallLimitMiddleware` | 限制模型调用次数 | `run_limit=100` |
| `ContextEditingMiddleware` | 清理旧 tool 结果节省 token | `edits=[ClearToolUsesEdit(trigger=100000)]` |

### 5.2 自定义中间件模式

```python
from langchain.agents.middleware import (
    AgentMiddleware, before_model, after_model, after_agent, wrap_model_call
)

# 钩子装饰器方式
@before_model
def add_context(state, runtime) -> dict | None:
    """在每次模型调用前注入额外上下文。返回 None = 不修改。"""
    user_info = runtime.store.get(("users",), runtime.context.user_id)
    return {"system_prompt": f"Current user: {user_info}"} if user_info else None

@after_model  
def log_response(state, runtime) -> None:
    """模型返回后记录日志。"""
    last_msg = state["messages"][-1]
    logger.info(f"Model response: {last_msg.content[:100]}")

@after_agent
def final_check(state, runtime) -> dict | None:
    """Agent 结束前的最终校验。可以更新 state 或返回 None。"""

# 类方式（需要跨钩子共享状态时）
class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state, runtime):
        self.call_count = getattr(self, 'call_count', 0) + 1

agent = create_agent(model, tools=tools, middleware=[add_context, log_response])
```

---

## 6. 结构化输出

```python
from pydantic import BaseModel, Field
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy

class ContactInfo(BaseModel):
    name: str = Field(description="Person's name")
    email: str = Field(description="Email address")
    phone: str = Field(description="Phone number")

# 方式1: 直接传 schema（自动选策略）
agent = create_agent(model="gpt-5.4", tools=[...], response_format=ContactInfo)

# 方式2: 显式 ToolStrategy（兼容所有模型）
agent = create_agent(model=..., response_format=ToolStrategy(
    schema=ContactInfo,
    handle_errors=True,  # 校验失败自动重试
))

# 方式3: ProviderStrategy（OpenAI/Anthropic 原生支持，最高可靠性）
agent = create_agent(model="gpt-5.4", response_format=ProviderStrategy(ContactInfo))

# 获取结果
result = agent.invoke({"messages": [...]})
result["structured_response"]  # ContactInfo(name=..., email=..., phone=...)
```

---

## 7. 记忆

### 7.1 短期记忆（对话持久化）

```python
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.utils.uuid import uuid7

agent = create_agent(model, tools=[...], checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": str(uuid7())}}

# thread_id 相同 → 自动记住上文
agent.invoke({"messages": [{"role": "user", "content": "我叫 Bob"}]}, config=config)
agent.invoke({"messages": [{"role": "user", "content": "我叫什么?"}]}, config=config)
# → "你叫 Bob"

# 生产环境：PostgresSaver / LangSmith 自动配置
```

### 7.2 长期记忆（跨对话持久化）

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
agent = create_agent(model, tools=[...], store=store)

# 工具内通过 runtime.store 读写
@tool
def remember_pref(key: str, value: str, runtime: ToolRuntime) -> str:
    runtime.store.put(("user_prefs",), runtime.context.user_id, {key: value})
    return f"Saved {key}={value}"

# 生产环境：PostgresStore
```

### 7.3 扩展 Agent State

```python
from langchain.agents import AgentState

class CustomAgentState(AgentState):
    user_name: str = ""
    access_level: str = "basic"

agent = create_agent(model, tools=[...], state_schema=CustomAgentState)
```

### 7.4 管理长对话的四种策略

| 策略 | 实现 |
|------|------|
| Trim（裁剪） | `SummarizationMiddleware` 自动压缩 |
| Delete（删除） | `RemoveMessage` + `REMOVE_ALL_MESSAGES` |
| Summarize（摘要） | `SummarizationMiddleware(model=..., trigger=("messages", 20))` |
| Custom（自定义） | `@before_model` 钩子中修改 messages |

---

## 8. 流式输出

```python
# v2 流式 — stream_mode 多模式
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    config=config,
    stream_mode=["messages", "updates"],
    version="v2",
):
    if mode == "messages":
        msg_chunk, metadata = chunk
        print(msg_chunk.content, end="", flush=True)

# v3 事件流 — 类型投影（推荐新项目）
for event in agent.stream_events(
    {"messages": [{"role": "user", "content": "..."}]},
    config=config,
    version="v3",
):
    text = event.get("text")           # 文本增量
    reasoning = event.get("reasoning") # 思考过程
    tool_calls = event.get("tool_calls")  # 工具调用
    output = event.get("output")       # 最终输出
```

---

## 9. 多智能体 — 五种模式速查

| 模式 | 适用场景 | 特点 |
|------|---------|------|
| **Subagents** | 并行处理、独立上下文 | 主 agent 分发 → 子 agent 各自上下文 → 汇总 |
| **Handoffs** | 客服转接、多领域对话 | agent 之间直接转接，用户无感 |
| **Skills** | 按需加载领域知识 | 通过 `SkillsMiddleware` 注入 |
| **Router** | 简单分类分发 | LLM 分类 → 条件边路由 |
| **Custom Workflow** | 复合流程 | LangGraph StateGraph 自定义 |

```python
# Subagents 模式（最常用）
from deepagents.middleware import SubAgentMiddleware

subagents = [{
    "name": "researcher",
    "description": "Searches and returns structured summaries",
    "tools": [search],
}]
agent = create_agent(model, tools=[search],
    middleware=[SubAgentMiddleware(subagents=subagents)])
```

详细 → `references/patterns.md`

---

## 10. Human-in-the-Loop

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command

agent = create_agent(model, tools=[send_email, delete_user],
    checkpointer=InMemorySaver(),  # HITL 必须！
    middleware=[HumanInTheLoopMiddleware(interrupt_on={
        "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
        "delete_user": True,
    })])

# 首次调用 → 触发中断
result = agent.invoke({"messages": [...]}, config={"configurable": {"thread_id": "t1"}})
# result.interrupts[0] → 中断信息

# 审批后恢复（同一 thread_id）
result = agent.invoke(Command(resume={"type": "approve"}),
    config={"configurable": {"thread_id": "t1"}})
```

---

## 11. 常见报错速查

| 报错 | 原因 | 修复 |
|------|------|------|
| `ModuleNotFoundError: langchain.chains` | 旧链已移除 | `pip install langchain-classic` |
| `create_agent() got unexpected keyword 'state_modifier'` | v1 改名 | 用 `system_prompt` |
| `cannot import 'create_react_agent'` | 旧版 | `from langchain.agents import create_agent` |
| pre-bound model 报错 | 模型被预绑定 | 不要对 `create_agent` 传 `model.bind_tools()` 后的模型 |
| `NodeInterrupt is deprecated` | v1 改名 | 用 `GraphInterrupt` |
| HITL 不生效 | 缺 checkpointer | `checkpointer=InMemorySaver()` 必须 |

---

## 12. 执行协议

1. **绝不使用旧版 API** — 见第1节黑名单
2. **优先 create_agent()** — 不要降级到 LangGraph 除非确有必要
3. **定制行为用 middleware** — 先查内置列表，没有再自定义
4. **需要详细 API** → `references/api-reference.md`
5. **旧项目迁移** → `references/migration-comparison.md`
6. **图模式 / 多智能体** → `references/patterns.md`
7. **MCP 集成** → `references/mcp-integration.md`
8. **选型决策（该不该用 LC）** → `references/decision-guide.md`
