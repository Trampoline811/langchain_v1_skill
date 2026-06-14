---
name: langgraph-v1
description: LangGraph v1 底层编排框架代码生成规范。提供 StateGraph/Functional API、持久化、中断、子图、流式、容错等底层能力。当用户需要自定义图拓扑、混合确定性与智能体工作流时使用。触发词：langgraph、StateGraph、图编排、persistence、持久化、interrupts、中断、subgraphs、子图、条件边、functional API、@entrypoint、@task、Send API、checkpointer、InMemorySaver、SqliteSaver。
---

# LangGraph v1 编码规范

> LangGraph 是 **Agent Runtime**（代理运行时），负责 durable execution、streaming、HITL、persistence。
> LangChain 官方定位：LangGraph ≈ Temporal/Inngest 级别的 durable execution engine，同时兼有 Framework 属性。
> — Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)
>
> **先用 `create_agent()`，不够了再降级到 LangGraph。** 绝大多数场景 `create_agent()` 足够。

## 与 LangChain 的关系

```
DeepAgents  ← Agent Harness（预组装电池包，规划/文件系统/子Agent 全内置）
    │
LangChain   ← Agent Framework（create_agent, @tool, middleware）
    │         ⚠️ LangChain 1.0 的 agent loop 跑在 LangGraph runtime 之上
    │
LangGraph   ← Agent Runtime（durable execution / streaming / HITL / persistence）
               Harrison 原话："LangGraph is probably best described as
               both a runtime and a framework."
```

**LangGraph 不依赖 LangChain** — 可以不装 `langchain` 直接用 `langgraph` 构建纯数据处理图。反过来，**LangChain 依赖 LangGraph** — `create_agent()` 底层由 StateGraph 驱动。
> 💡 不确定用哪个？→ `/agent-sdk-router`（LangChain 官方三选一决策表）

---

## 1. 两种 API

| API | 风格 | 适用场景 |
|-----|------|---------|
| **Graph API** | 显式 StateGraph builder | 复杂拓扑、条件路由、并行 |
| **Functional API** | `@entrypoint` / `@task` 装饰器 | 线性/简单分支、快速原型 |

---

## 2. Graph API

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# 1. 定义 State
class State(TypedDict):
    messages: list
    classification: str

# 2. 定义节点
def classify(state: State) -> dict:
    """每个节点返回 dict 更新 state"""
    return {"classification": "type_a"}

def handler_a(state: State) -> dict:
    return {"messages": [AIMessage(content="Handled by A")]}

# 3. 构建图
builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("handler_a", handler_a)
builder.add_edge(START, "classify")

# 条件边
def route(state: State) -> str:
    return state["classification"]  # 返回下一个节点名

builder.add_conditional_edges("classify", route, {
    "handler_a": "handler_a",
    "handler_b": "handler_b",
})
builder.add_edge("handler_a", END)

# 4. 编译
graph = builder.compile(checkpointer=checkpointer)
result = graph.invoke({"messages": [...]}, config)
```

### 关键 API

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, Send, GraphInterrupt

# Reducer（并行安全汇聚）
import operator
class State(TypedDict):
    results: Annotated[list, operator.add]  # 追加而非覆盖

# Command — 更新 state + 路由
def node(state) -> Command:
    return Command(update={"field": value}, goto="next_node")

# GraphInterrupt — 中断执行
def node(state) -> Command:
    return Command(interrupt={"reason": "需要人工审批", "data": state["plan"]})

# Send — 动态并行 fan-out
def assign_workers(state):
    return [Send("worker", {"task": t}) for t in state["tasks"]]
```

---

## 3. Functional API

```python
from langgraph.func import entrypoint, task
from langgraph.checkpoint.memory import InMemorySaver

@task
def step_a(data: str) -> str:
    return data.upper()

@task
def step_b(data: str) -> str:
    return f"Processed: {data}"

@entrypoint(checkpointer=InMemorySaver())
def workflow(input: str) -> str:
    a_result = step_a(input).result()
    b_result = step_b(a_result).result()
    return b_result
```

---

## 4. 持久化（Checkpointer）

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

# 开发
checkpointer = InMemorySaver()

# 本地
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# 生产
checkpointer = PostgresSaver.from_conn_string("postgresql://...")

# 使用
config = {"configurable": {"thread_id": "unique-thread-id"}}
graph.invoke({"messages": [...]}, config)
# 同一 thread_id → 自动恢复上下文
```

**checkpointer 是以下功能的前提：**
- Human-in-the-loop 中断/恢复
- 对话历史跨轮次持久化
- Thread-level 限制（`ModelCallLimitMiddleware.thread_limit`）
- Time travel 调试

---

## 5. 流式输出

```python
# 多模式流式
for mode, chunk in graph.stream(
    {"messages": [...]}, config,
    stream_mode=["messages", "updates", "values", "events"],
):
    if mode == "messages":   # token 级打字机
    elif mode == "updates":  # 状态增量
    elif mode == "values":   # 完整状态快照

# v3 事件流
for event in graph.stream_events({"messages": [...]}, config, version="v3"):
    event.get("text")
    event.get("tool_calls")
    event.get("output")
```

---

## 6. Human-in-the-Loop（中断/恢复）

```python
from langgraph.types import Command

# 图中断
def approval_node(state):
    return Command(interrupt={
        "action": "review",
        "data": state["pending"],
        "reason": "人工审批"
    })

# 首次调用 → 触发中断
result = graph.invoke({"input": "delete"}, config={"configurable": {"thread_id": "t1"}})
# result.interrupts → [GraphInterrupt(...)]

# 审批后恢复
result = graph.invoke(
    Command(resume={"approved": True}),
    config={"configurable": {"thread_id": "t1"}}  # 同一 thread_id
)
```

---

## 7. 子图（Subgraphs）

Agent 作为图的节点嵌入：

```python
from langchain.agents import AgentState, create_agent
from langgraph.graph import StateGraph, START

agent_node = create_agent("claude-sonnet-4-6", tools=[...], name="assistant")

graph = (
    StateGraph(AgentState)
    .add_node("classify", classify_node)
    .add_node("assistant", agent_node)   # Agent 即节点
    .add_edge(START, "classify")
    .add_conditional_edges("classify", route, {"assistant": "assistant", ...})
    .compile()
)
# Agent 的 middleware/checkpointer/streaming 完整保留在子图中
```

---

## 8. 容错

```python
# 节点级重试
from langgraph.types import RetryPolicy

builder.add_node("api_call", api_node,
    retry=RetryPolicy(
        max_attempts=3,
        backoff_factor=2.0,
        initial_interval=1.0,
        retry_on=(ConnectionError, TimeoutError),
    )
)
```

---

## 9. 何时用 LangGraph？

| 场景 | 用 create_agent() | 用 LangGraph |
|------|:--:|:--:|
| 标准 tool-calling loop | ✅ | ❌ 过度设计 |
| 多轮对话 + 记忆 | ✅ | ❌ |
| 确定性步骤 + 条件分支 | ❌ | ✅ |
| 并行 fan-out / fan-in | ❌ | ✅ |
| 多 Agent 间复杂路由 | ❌ | ✅ |
| Human-in-the-Loop（底层） | ❌ | ✅ |
| 纯数据处理 pipeline | ❌ | ✅ |

---

## 10. 执行协议

1. **先 create_agent，后 LangGraph** — 不要上来就写 StateGraph
2. **图要简单** — 节点超过 5-7 个考虑拆分
3. **State 用 TypedDict** — 字段尽量少，用 `Annotated[list, operator.add]` 安全汇聚
4. **checkpointer 不可缺** — 持久化 / HITL / 多轮对话都依赖它
5. **流式直接用 `stream_mode=["messages"]`** — 打字机效果最简单的方式

---

## 11. 设计模式

### 11.1 GraphConfig：按节点选模型

不同节点对模型能力要求不同——生成用廉价模型跑量，审查用强模型把关。

```python
from typing import TypedDict, Literal

class GraphConfig(TypedDict):
    draft_model: Literal["openai", "anthropic"]    # 生成节点
    critique_model: Literal["openai", "anthropic"]  # 审查节点

def draft(state, config):
    model_name = config["configurable"].get("draft_model", "openai")
    model = _get_model(model_name)
    ...

# 编译时声明 config schema
builder = StateGraph(State, config_schema=GraphConfig)
graph = builder.compile(checkpointer=checkpointer)

# 调用时按节点切换模型
graph.invoke(input, {"configurable": {"draft_model": "anthropic"}})
```

**原则**：生成/提取用便宜模型，审查/决策用强模型。GraphConfig 让调用方在 `invoke` 时切换，无需改图。

### 11.2 RemoveMessage：语境窗口管理

图中提取结构化信息后，对话历史不再有用——删掉释放窗口：

```python
from langchain_core.messages import RemoveMessage

def extract_requirements(state):
    """工具调用提取需求后，信息已结构化 → 清历史"""
    response = model.bind_tools([Build]).invoke(state["messages"])
    if response.tool_calls:
        requirements = response.tool_calls[0]["args"]["requirements"]
        # 清除对话历史，只保留结构化结果
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"]]
        return {"requirements": requirements, "messages": delete_messages}
    return {"messages": [response]}
```

**原则**：结构化提取完成 → 立即删历史。不要让无用对话吃掉后续节点的语境窗口。

### 11.3 多阶段质量环：程序化检查 + LLM 审查

一道检查不够。先程序化（格式/语法，零 token 成本），过了再 LLM 审查（语义/正确性）：

```
draft → check(程序化) → critique(LLM) → 通过? → END
  ↑         ↓ 格式错           ↓ 语义错        |
  └─────────└─────────────────┘  (loop back)   ✓
```

```python
import re

# 1. 程序化检查 —— 零 token 成本
def check(state):
    """正则提取代码块，格式不对直接打回"""
    code_blocks = re.findall(
        r'```python\s*(.*?)\s*```',
        state["messages"][-1].content, re.DOTALL
    )
    if not code_blocks:
        return {"messages": [
            {"role": "user", "content": "缺少代码块，请重新生成"}
        ]}
    return {"code": code_blocks[0]}

# 2. LLM 审查 —— 语义把关
class Accept(BaseModel):
    logic: str
    accept: bool

def critique(state, config):
    """LLM 审查代码正确性，输出 Accept(accept=True/False)"""
    model = _get_model(config, "anthropic", "critique_model")
    response = model.bind_tools([Accept]).invoke(critique_prompt + state["code"])
    return {"accepted": response.tool_calls[0]["args"]["accept"]}

# 3. 路由条件
def route_critique(state) -> Literal["draft", END]:
    return END if state["accepted"] else "draft"
```

**原则**：**先廉价后昂贵**。程序化检查能拦住的（格式错、缺少代码块、多代码块）绝不浪费 LLM 调用。
