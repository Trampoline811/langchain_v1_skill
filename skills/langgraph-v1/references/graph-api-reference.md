# LangGraph Graph API 完整参考

> **来源**: 官方 `langgraph-graph-api.md` (1753行) + `langgraph-use-graph-api.md` (117507字)
> **定位**: API 速查手册 — 完整签名、参数说明、返回类型。教程级内容见 `SKILL.md`。

---

## 1. StateGraph Builder

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(StateSchema)
# StateSchema: TypedDict | Pydantic BaseModel | dataclass
```

### builder 方法链

| 方法 | 签名 | 说明 |
|------|------|------|
| `add_node` | `add_node(name: str, action: Runnable \| Callable, *, retry: RetryPolicy = None, timeout: float = None, idle_timeout: float = None)` | 注册节点 |
| `add_edge` | `add_edge(from_node: str, to_node: str)` | 普通边 |
| `add_conditional_edges` | `add_conditional_edges(source: str, router: Callable, path_map: dict[str, str])` | 条件路由 |
| `compile` | `compile(*, checkpointer=None, store=None, retry=None, name=None, config_schema=None, interrupt_before=None, interrupt_after=None, debug=False)` | 编译为 Runnable |

---

## 2. State 定义

### TypedDict（推荐）

```python
from typing import TypedDict, Annotated
import operator


class MyState(TypedDict):
    messages: list                           # 默认覆盖
    results: Annotated[list, operator.add]   # Reducer: 并行安全追加
    count: int                               # 覆盖
```

### Reducers

| Reducer | 行为 | 适用场景 |
|---------|------|---------|
| 默认（无 Annotated） | **覆盖** — 后写入覆盖前值 | 单一来源字段 |
| `operator.add` | **追加** — 新值追加到列表 | 并行 fan-out 汇聚 |
| 自定义函数 | `def my_reducer(left, right) -> merged` | 自定义合并逻辑 |

### MessagesState（快捷方式）

```python
from langgraph.graph import MessagesState

# 等价于:
class MessagesState(TypedDict):
    messages: Annotated[list, operator.add]
```

---

## 3. 节点

### 节点函数签名

```python
# 基础
def my_node(state: State) -> dict:
    """返回 dict 更新 state"""
    return {"field": value}

# 带 config（访问 checkpointer/store/thread_id）
def my_node(state: State, config: RunnableConfig) -> dict:
    thread_id = config["configurable"]["thread_id"]
    return {"field": value}

# 返回 Command（更新 + 路由）
def my_node(state: State) -> Command:
    return Command(update={"field": value}, goto="next_node")
```

### START / END

```python
from langgraph.graph import START, END

builder.add_edge(START, "first_node")   # 入口
builder.add_edge("last_node", END)      # 出口
```

---

## 4. 条件边

```python
def router(state: State) -> str:
    """返回下一个节点名"""
    if state["score"] > 0.8:
        return "approved"
    return "review"

builder.add_conditional_edges(
    "classify",          # 源节点
    router,              # 路由函数 → 返回 str
    {
        "approved": "approve_handler",
        "review": "review_handler",
    },
)

# 条件入口（动态选择起始节点）
builder.add_conditional_edges(START, entry_router, {
    "path_a": "node_a",
    "path_b": "node_b",
})
```

---

## 5. Command（状态更新 + 路由 + 中断）

```python
from langgraph.types import Command

# 更新 + 路由
Command(update={"field": value}, goto="next_node")

# 路由到指定 graph（跨图编排）
Command(update={...}, graph="other_graph")

# 中断执行（Human-in-the-Loop）
Command(interrupt={"reason": "需要审批", "data": state["plan"]})

# 恢复执行
Command(resume={"approved": True})

# 工具内返回 Command
@tool
def my_tool(x: str) -> Command:
    return Command(update={"result": x}, goto="next_step")
```

---

## 6. Send（动态并行 Fan-out）

```python
from langgraph.types import Send

def dispatcher(state: State) -> list[Send]:
    """为每个任务创建一个并行 worker"""
    return [
        Send("worker", {"task": task})
        for task in state["tasks"]
    ]

builder.add_conditional_edges("dispatcher", dispatcher, {"worker": "worker"})
# worker 节点会被并行执行 N 次（N = len(tasks)）
```

---

## 7. GraphInterrupt（中断）

```python
from langgraph.types import GraphInterrupt

# 节点内触发中断
def approval_node(state: State) -> Command:
    return Command(interrupt=GraphInterrupt(
        action="review_document",
        data=state["draft"],
        reason="需要人工审核文档内容",
    ))

# 调用方检查中断
result = graph.invoke({"input": "..."}, config)
if hasattr(result, "interrupts"):
    for interrupt in result.interrupts:
        print(f"中断: {interrupt.action} — {interrupt.reason}")
```

> **前提**: checkpointer 必须设置。中断信息存在 checkpoint 中，恢复时读取。

---

## 8. GraphConfig（按调用切换行为）

```python
from typing import TypedDict


class GraphConfig(TypedDict):
    model: str
    max_retries: int

# 编译时声明
graph = builder.compile(config_schema=GraphConfig)

# 调用时传入
graph.invoke(input, {"configurable": {
    "thread_id": "t1",
    "model": "anthropic",
    "max_retries": 5,
}})

# 节点内读取
def my_node(state, config):
    model = config["configurable"].get("model", "openai")
```

---

## 9. checkpointer + store（编译时注入）

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

graph = builder.compile(
    checkpointer=InMemorySaver(),   # 短期记忆（单线程状态）
    store=InMemoryStore(),          # 长期记忆（跨线程共享）
)

config = {"configurable": {"thread_id": "unique-id"}}
graph.invoke({"messages": [...]}, config)
# 同一 thread_id → 自动恢复状态
```

### 编译参数速查

| 参数 | 类型 | 说明 |
|------|------|------|
| `checkpointer` | `BaseCheckpointer` | 状态持久化（必需于 HITL / 多轮对话） |
| `store` | `BaseStore` | 跨线程长期记忆 |
| `retry` | `RetryPolicy` | 所有节点的默认重试策略 |
| `config_schema` | `type` | 调用方 config 的类型约束 |
| `interrupt_before` | `list[str]` | 在这些节点执行前自动中断 |
| `interrupt_after` | `list[str]` | 在这些节点执行后自动中断 |
| `name` | `str` | 图名（日志/追踪用） |
| `debug` | `bool` | 开启调试日志 |

---

## 10. `[社区]` 社区实践补充

### Windows 路径兼容

```python
# ❌ Windows 反斜杠导致 StateGraph 序列化失败
root_dir = "C:\\Users\\data"

# ✅ 统一用正斜杠
root_dir = "C:/Users/data"
```

### 节点错误隔离

```python
# 社区验证：节点内 try/except + Command 路由比 RetryPolicy 更可靠
def resilient_api_node(state) -> Command:
    try:
        data = call_external_api(state["query"])
        return Command(update={"api_result": data}, goto="process")
    except TimeoutError:
        return Command(update={"api_result": None}, goto="fallback")
    except Exception as e:
        return Command(update={"error": str(e)}, goto="error_handler")
```

### 并行 fan-out 最佳实践

```python
# ✅ Send 中传最小必要数据（不是整个 state）
def dispatcher(state):
    return [Send("worker", {"task_id": i, "payload": t["data"]}) for i, t in enumerate(state["tasks"])]

# ❌ 传整个 state → 并行 worker 互相覆盖
def bad_dispatcher(state):
    return [Send("worker", state) for _ in state["tasks"]]
```

---

> **返回**: [`SKILL.md`](../SKILL.md) §2 Graph API | §7 子图 | §11 设计模式
