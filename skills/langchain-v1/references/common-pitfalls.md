# 高频踩坑合集

> **来源**: AgentSeek `common-issues.md` + `middleware.md` + `streaming.md`（ob-labs/agentseek），社区实战验证
> **定位**: 工程实践中高频遇到的非预期行为、排障流程、修复方案。每一条都是踩过的坑。
> **文中标记**: `[社区]` = AgentSeek 社区踩坑经验

---

## 1. 工具返回值的三种语义 `[社区]`

### 症状

工具返回内容有时被模型看到但 app 层拿不到，有时 app 层拿到了却污染了 LLM 上下文。

### 原因

一个 tool 的返回值有三类消费者，需要走三条不同的通道：

| 消费者 | 通道 | 说明 |
|--------|------|------|
| **模型（LLM）** — 决定下一步 | `ToolMessage.content` | 内容进入模型上下文，模型据此决策 |
| **应用层/业务代码** — 但不进 LLM 上下文 | `ToolMessage(artifact=...)` | 文档 ID、原始 payload、渲染提示等元数据 |
| **Agent state** — 后续 tool / middleware 读取 | `Command(update=...)` | `customer_id`、`last_order`、`current_step` 等状态字段 |

错误姿势：把所有数据挤到 `content` 字符串里。

### 正确姿势

```python
from langchain.messages import ToolMessage
from langgraph.types import Command
from langchain.tools import tool, ToolRuntime

# 场景1: 只给模型看 → 直接 return str
@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Sunny in {city}, 22°C"

# 场景2: 给模型看 + 元数据给 app → ToolMessage(artifact=...)
@tool
def search_books(query: str, runtime: ToolRuntime) -> ToolMessage:
    """检索书籍，附带来源元数据"""
    passage = "It was the best of times..."
    return ToolMessage(
        content=passage,                    # 进模型上下文
        artifact={"doc_id": "bk001"},       # 不进模型，app 层从 ToolMessage 读取
        tool_call_id=runtime.tool_call_id,
    )

# 场景3: 写 state 给后续节点看 → Command(update=...)
@tool
def save_user_profile(name: str, email: str, runtime: ToolRuntime) -> Command:
    """保存用户信息到 agent state"""
    return Command(update={
        "user_name": name,
        "user_email": email,
        "messages": [ToolMessage(
            f"Profile saved: {name}",
            tool_call_id=runtime.tool_call_id,
        )],
    })
```

### 核心原则

三种通道可同时使用，互不冲突：一次 tool 返回可以同时有 `content`（给模型）、`artifact`（给 app）、`Command(update=...)`（给 state）。

---

## 2. with_structured_output 返回 None `[社区]`

### 症状

使用 `model.with_structured_output(schema)` 或 `create_agent(response_format=schema)` 获取结构化结果，偶尔返回 `None`、空对象、或缺失字段。同一 prompt 多次运行，时好时坏。模型越小（小参数、开源、量化），越严重。

### 原因

`with_structured_output` 有三种底层实现（`method` 参数），默认大多数模型走 **`function_calling`** — 本质是"给模型绑一个 schema 形状的 tool，让模型通过 tool_call 输出结构化数据"。但绑定后**模型有自由选择是否调用该 tool**，弱模型常常直接自然语言回复，不产生 tool_call → 解析阶段拿不到结构化结果 → 返回 `None`。

### 三级升级修复

按以下顺序递进，上一级不行再下一级：

```python
from pydantic import BaseModel

class MyOutput(BaseModel):
    summary: str
    score: float

# 级别1（最可靠）：Provider 原生 json_schema
# OpenAI structured outputs / Gemini structured output 在解码层强制 schema
from langchain.agents.structured_output import ProviderStrategy
agent = create_agent(
    model="openai:gpt-5.5",
    response_format=ProviderStrategy(MyOutput),
)

# 级别2：json_mode — 强制输出 JSON，但不保证字段完整性
agent = create_agent(
    model="google_genai:gemini-2.5-flash",
    response_format=ToolStrategy(
        schema=MyOutput,
        handle_errors=True,       # 校验失败自动重试
        tool_message_content="Please output valid JSON matching the schema",
    ),
)

# 级别3（兜底）：用普通 tool + structured_output 工具,
# 在 @after_model 中检测 None 并手动重试
@after_model
def retry_on_none(state, runtime) -> dict | None:
    if state.get("structured_response") is None:
        return {"system_prompt": "你必须调用 output 工具返回结构化数据，不能只自然语言回复"}
    return None
```

### 经验教训

- 不要假设 LLM 一定会按 schema 输出。用 ProviderStrategy 最可靠。
- 弱模型（7B/13B 开源模型）走 `json_mode` 后仍需 `handle_errors=True` 二次兜底
- 极端情况：加 `@after_model` 钩子检测 `None` 并强制重试

---

## 3. MCP 工具无法访问 runtime context `[社区]`

### 症状

MCP 工具（通过 `MultiServerMCPClient` 加载）在运行时拿不到 `user_id`、`store`、`state` 等上下文信息。

### 原因

MCP 工具运行在**独立进程**中，不共享 LangGraph runtime 的内存空间。`ToolRuntime` 注入仅适用于 `@tool` 装饰的 Python 函数，MCP 工具无此机制。

### 修复

```python
# 方案A: 用 before_model 钩子把 runtime 数据注入到 system_prompt
@before_model
def inject_context_for_mcp(state, runtime) -> dict | None:
    user_id = runtime.context.user_id if runtime.context else "unknown"
    return {
        "system_prompt": (
            f"[Context] current user_id: {user_id}\n"
            "MCP tools 需要 user_id 时从 system prompt 中提取"
        )
    }

# 方案B: 包装 MCP 工具为 Python @tool，在包装层传入 context
from langchain.tools import tool, ToolRuntime

@tool
async def wrapped_search(query: str, runtime: ToolRuntime) -> str:
    """包装 MCP search 工具，注入 context"""
    user_id = runtime.context.user_id
    # 用 user_id 修饰 query 或作为额外参数传给 MCP tool
    # actual_mcp_result = await mcp_search(query, user_id=user_id)
    ...
```

---

## 4. 流式输出常见坑 `[社区]`

### 4.1 stream_events vs stream 区别

| 维度 | `stream(stream_mode=...)` | `stream_events(version="v3")` |
|------|------|------|
| 返回类型 | generator，混合所有事件按时间排序 | `Stream` 对象，按类型投影分组 |
| 业务分发 | 业务侧用 if/elif 按 mode/type 分发 | 业务侧读对应属性 iterator |
| 多 LLM token 源 | 混在一起，需手动区分 | 每个 event 有 `event` 字段声明来源 |
| 推荐 | 旧项目兼容 | **新项目默认** |

```python
# ✅ v3 — 每个 event 自带类型投影
stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "..."}]},
    version="v3",
)

for event in stream:
    if text := event.get("text"):            # 文本 token
        print(text, end="", flush=True)
    if reasoning := event.get("reasoning"):  # 思考过程
        print(f"[思考] {reasoning}")
    if tool_calls := event.get("tool_calls"):  # 工具调用
        print(f"[调用工具] {tool_calls}")
```

### 4.2 自定义进度事件（工具内）

```python
@tool
def long_running_task(query: str, runtime: ToolRuntime) -> str:
    """工具内发送进度事件"""
    # 在工具执行中写 stream，LLM 和 app 层都能收到
    runtime.stream_writer({"type": "progress", "step": "fetching", "pct": 0})
    data = fetch_data(query)
    runtime.stream_writer({"type": "progress", "step": "processing", "pct": 50})
    result = process(data)
    runtime.stream_writer({"type": "progress", "step": "done", "pct": 100})
    return result

# app 层用 v2 stream_mode="custom" 接收自定义事件
for mode, chunk in agent.stream({...}, stream_mode=["custom"], version="v2"):
    print(f"Progress: {chunk}")  # {"type": "progress", "step": "fetching", "pct": 0}
```

> ⚠️ `stream_writer` 写的内容只在 `stream_mode="custom"` + `version="v2"` 中可见。v3 暂不直接支持自定义事件，需包在 `ToolMessage` 中传递。

### 4.3 多 LLM token 源区分

当 agent 用了多个模型（如 subagent），v2 的 `messages` mode 会把所有模型的 token 混在一起：

```python
# v2: 需手动通过 metadata 区分来源
for mode, chunk in agent.stream({...}, stream_mode=["messages"], version="v2"):
    if mode == "messages":
        msg_chunk, metadata = chunk
        source = metadata.get("langgraph_node")  # 哪个节点产生的 token
        print(f"[{source}] {msg_chunk.content}")

# v3: event 自带 event 字段区分来源（推荐）
for event in agent.stream_events({...}, version="v3"):
    print(f"[{event['event']}] {event.get('text', '')}")
```

### 4.4 禁用特定模型的流式

```python
# 部分国产模型流式不稳定 → 通过 init_chat_model 参数关闭
model = init_chat_model(
    "openai:qwen-max",
    base_url="...",
    streaming=False,  # 强制非流式
)
```

---

## 5. 中间件执行顺序（洋葱模型）`[社区]`

### 症状

多个 middleware 组合时，hooks 执行顺序不直观，state 被意外覆盖、逻辑失效。

### 原因

中间件执行遵循**洋葱模型**：

```
middleware=[m1, m2, m3]  ← 列表顺序

执行顺序：
  before_model:  m1 → m2 → m3    （列表正序）
  wrap_model_call: m1 → m2 → m3  （列表正序，嵌套包裹）
  after_model:   m3 → m2 → m1    （反序！）
  before_agent:  m1 → m2 → m3    （正序）
  after_agent:   m3 → m2 → m1    （反序）
```

### 核心规则

- 需要**最早拦截**的放列表最前面（速率限制、权限检查）
- 需要**最后兜底**的也放最前面（wrap 嵌套中外层最后执行）
- `wrap_model_call` 的嵌套：第一个 middleware 同时最早收到请求**和**最晚收到响应

### 如何验证

```python
class DebugMiddleware(AgentMiddleware):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def before_model(self, state, runtime):
        print(f"[{self.name}] before_model")
        return None

    def after_model(self, state, runtime):
        print(f"[{self.name}] after_model")
        return None

# middleware=[DebugMiddleware("A"), DebugMiddleware("B"), DebugMiddleware("C")]
# 输出:
# [A] before_model
# [B] before_model
# [C] before_model
# [C] after_model    ← 注意反序！
# [B] after_model
# [A] after_model
```

---

## 6. wrap_model_call 内修改 state 无效 `[社区]`

### 症状

在 `@wrap_model_call` 里修改 state，下游拿不到修改后的值。

### 原因

`wrap_model_call` 的参数 `request` 和 `response` 是**快照副本**，直接修改不写回。

### 修复

```python
# ❌ 无效 — 修改 request/response 副本
@wrap_model_call
def bad_modify(request, handler):
    request.state["custom_field"] = "value"  # 不会影响实际 state
    return handler(request)

# ✅ 正确 — 通过 request.override() 创建新请求
@wrap_model_call
def correct_modify(request, handler):
    request = request.override(
        model="claude-sonnet-4-6",  # 切换模型
        system_prompt="Overridden",
    )
    return handler(request)

# ✅ 正确 — 在 after_model 中修改 state
@after_model
def modify_state_in_after(state, runtime) -> dict:
    return {"custom_field": "value"}  # 合并到 state
```

---

> **返回**: [`SKILL.md`](../SKILL.md) §11 常见报错速查 | §5 中间件 | `references/api-reference.md`
