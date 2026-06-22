# 图模式参考

> **来源**: 官方 `langchain-multi-agent/*.md` (5 种模式) + 官方 `langgraph-workflows-agents.md` (4 种底层图模式) + AgentSeek `multi-agent.md` + `streaming.md`（社区排坑）
> **定位**: 包含 create_agent 多智能体模式（5 种）+ LangGraph 底层图模式（4 种）+ 流式最佳实践 + Subagents vs Handoffs 决策。
> **文中标记**: 无标记 = 官方文档 | `[社区]` = 社区实战案例验证

## create_agent 多智能体模式（5 种）`[官方]`

| 模式 | 方式 | 场景 |
|------|------|------|
| **Subagents** | `SubAgentMiddleware(subagents=[...])` | 并行处理、独立上下文 |
| **Handoffs** | `HandoffMiddleware(handoff_targets=[...])` | 客服转接、多领域 |
| **Skills** | `SkillsMiddleware(backend=..., sources=[...])` | 按需加载领域知识 |
| **Router** | `create_agent(...).as_tool()` 嵌套 | 简单分类分发 |
| **Custom Workflow** | LangGraph StateGraph 自定义 | 复合流程 |

Router 模式（最简）:
```python
general = create_agent("openai:gpt-5.4", tools=[...])
code_expert = create_agent("openai:gpt-5.4", tools=[code_tools])
router = create_agent("openai:gpt-5-nano", tools=[
    general.as_tool(name="general_assistant", description="General questions"),
    code_expert.as_tool(name="code_expert", description="Coding questions"),
])
```

---

## `[官方]` LangGraph 底层图模式（4 种）

> 四个官方认可的图模式，每个都有完整代码。源自 `workflows-agents.md`。

## Router（路由分类）

**用途：** 一条输入 → LLM 判断类型 → 分流到不同处理路径。适合"简单 vs 复杂"分支场景。

```
输入 → classify（LLM 判断）
         ├── "type_a" → handler_a → END
         └── "type_b" → handler_b → END
```

```python
class State(TypedDict):
    input: str
    classification: str
    output: str

def classify(state):
    result = model.with_structured_output(Route).invoke(state["input"])
    return {"classification": result.type}

def route(state):
    return state["classification"]  # 返回下一个节点名

builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("handler_a", handler_a)
builder.add_node("handler_b", handler_b)
builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route, {
    "handler_a": "handler_a",
    "handler_b": "handler_b",
})
```

**为什么不用 Agent 自由决策：** LLM 的分类结果被图拓扑"捕获"为确定性的路由——`route()` 返回什么就走哪个节点，不会发散。

---

## Orchestrator-Worker（编排-执行）

**用途：** 一个复杂任务 → LLM 拆成 N 个子任务 → 并行执行 → 汇总。适合多路并行检索、批量处理。

```
planner（拆子任务）
  → Send API 动态创建 Worker
     ├── Worker(task_1) ─┐
     ├── Worker(task_2) ─┤ 并行执行
     └── Worker(task_3) ─┘
  → 结果汇聚到共享 state
  → synthesizer（汇总）
```

```python
import operator
from langgraph.types import Send

# 主图 State
class State(TypedDict):
    input: str
    tasks: list[dict]              # [{id, payload}, ...]
    results: Annotated[list, operator.add]  # ← add reducer，并行安全
    final_output: str

# Worker State
class WorkerState(TypedDict):
    task: dict
    result: str

def planner(state):
    """LLM 拆分子任务"""
    plan = model.with_structured_output(Plan).invoke(state["input"])
    return {"tasks": plan.tasks}

def assign_workers(state):
    """每个子任务创建一个 Worker，LangGraph 并行执行"""
    return [Send("worker", {"task": t}) for t in state["tasks"]]

def worker(state: WorkerState):
    """单个 Worker 执行子任务"""
    result = do_work(state["task"])  # 实际的业务逻辑
    return {"result": result}

def synthesizer(state):
    """汇总所有 Worker 输出"""
    combined = "\n---\n".join(state["results"])
    final = model.invoke(f"汇总以下结果:\n{combined}")
    return {"final_output": final.content}

builder = StateGraph(State)
builder.add_node("planner", planner)
builder.add_node("worker", worker)
builder.add_node("synthesizer", synthesizer)
builder.add_edge(START, "planner")
builder.add_conditional_edges("planner", assign_workers, ["worker"])
builder.add_edge("worker", "synthesizer")
builder.add_edge("synthesizer", END)
graph = builder.compile()
```

**关键机制：**
- `Send("worker", {...})` — 动态创建 Worker，每个拿不同输入
- `Annotated[list, operator.add]` — 并行 Worker 输出自动追加，不冲突
- 子任务无依赖时天然并行执行

---

## Evaluator-Optimizer（评估-优化）

**用途：** 生成 → 评估 → 不通过则带反馈重新生成，循环至达标。适合有明确质量指标的答案质量控制。

```
generate → evaluate
             ├── "pass" → END
             └── "fail" → 带反馈回 generate（循环）
```

```python
class State(TypedDict):
    output: str
    feedback: str
    quality: str  # "pass" | "fail"

def generate(state):
    feedback = state.get("feedback", "")
    result = model.invoke(f"生成内容。上次反馈：{feedback}" if feedback else "生成内容")
    return {"output": result.content}

def evaluate(state):
    score = model.with_structured_output(QualityCheck).invoke(state["output"])
    return {"quality": score.grade, "feedback": score.feedback}

def route(state):
    return END if state["quality"] == "pass" else "generate"

builder = StateGraph(State)
builder.add_node("generate", generate)
builder.add_node("evaluate", evaluate)
builder.add_edge(START, "generate")
builder.add_edge("generate", "evaluate")
builder.add_conditional_edges("evaluate", route, {
    "generate": "generate", END: END
})
```

**用途举例：** 答案数值精度检查、翻译质量迭代、内容合规审查。

---

## Human-in-the-Loop（人工审批）

**用途：** 关键操作执行前暂停，等待人工审批后继续。官方标注适用 "database writes, financial transactions"。

### 方案 A：Graph API 节点内显式中断（推荐审计场景）

```python
from langgraph.types import Command

def sensitive_step(state):
    """interrupt() 函数 → 抛出 GraphInterrupt，暂停执行"""
    if needs_review(state):
        approved = interrupt({
            "action": "review_required",
            "data": state["pending_action"],
            "reason": "该操作需要人工确认",
        })
        # 客户端用 Command(resume=...) 恢复后，interrupt() 返回 resume 值
        if not approved:
            return {"blocked": True}
    return {"approved": True}

# 调用方 — 首次触发中断
result = graph.invoke({"input": ...})
# 检查中断: result["__interrupt__"]
if "__interrupt__" in result:
    interrupt_info = result["__interrupt__"]
    print(interrupt_info[0].value)  # 展示给审核人

    # 审核后恢复（同一 thread_id）
    result = graph.invoke(
        Command(resume={"approved": True}),
        config={"configurable": {"thread_id": "same-thread"}}
    )
```

### 方案 B：HumanInTheLoopMiddleware（适用于 create_agent）

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_agent(
    model, tools,
    middleware=[HumanInTheLoopMiddleware(interrupt_on={"critical_tool": True})],
    checkpointer=InMemorySaver(),
)
agent.invoke(Command(resume={"approved": True}), config=config)
```

**选择：** 方案 A 更白盒、可定制审计日志。方案 B 更简洁。审计场景推荐方案 A。

---

## `[社区]` 流式输出最佳实践

### stream_events v3 vs stream v2

| 维度 | `stream(stream_mode=...)` | `stream_events(version="v3")` |
|------|------|------|
| 返回类型 | generator 混合所有事件 | `Stream` 对象，按类型投影 |
| 业务分发 | 按 mode/type 手写 if/elif | 读对应属性 iterator |
| 多 LLM token 源 | 混在一起，需手动区分 | event 自带来源字段 |
| 推荐场景 | 旧项目兼容 | **新项目默认** |

```python
# v3 — 类型投影
stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "..."}]},
    version="v3",
)
for event in stream:
    text = event.get("text")            # 文本 token
    reasoning = event.get("reasoning")  # 思考过程
    tool_calls = event.get("tool_calls")  # 工具调用
    output = event.get("output")        # 最终输出
```

### 工具内自定义进度事件

```python
@tool
def long_task(query: str, runtime: ToolRuntime) -> str:
    runtime.stream_writer({"type": "progress", "step": "fetching", "pct": 0})
    data = fetch(query)
    runtime.stream_writer({"type": "progress", "step": "done", "pct": 100})
    return process(data)

# app 层接收
for mode, chunk in agent.stream({...}, stream_mode=["custom"], version="v2"):
    print(f"Progress: {chunk}")  # {type: "progress", step: "fetching", pct: 0}
```

> ⚠️ `stream_writer` 只在 `stream_mode="custom"` + `version="v2"` 中可见。

---

## `[社区]` 多智能体选型：Subagents vs Handoffs

选择错误会导致：主 agent 拿不到子 agent 输出，或子 agent 无法直接与用户对话。

| 需求 | 选型 |
|------|------|
| 主 agent 需要子 agent 结果来决策下一步 | **Subagents**（同步调用） |
| 子 agent 需干净上下文，不污染主对话 | **Subagents**（上下文隔离） |
| 多领域（日历/邮件/CRM）集中路由 | **Subagents** |
| 客服流程：收集保修ID → 退款，按顺序解锁 | **Handoffs** |
| 不同阶段需要不同 system prompt 和工具 | **Handoffs** |
| 子 agent 直接与用户对话，状态跨轮保持 | **Handoffs** |

**Subagents** — 主 agent 把子 agent 当 tool 调用，每次从干净上下文开始，结果返回主 agent。
**Handoffs** — 一个 tool 更新状态变量（如 `active_agent`），当前活跃 agent 直接接管用户对话。

```python
# Subagents 模式
agent = create_agent(model, tools=[...],
    middleware=[SubAgentMiddleware(subagents=[researcher, coder])])

# Handoffs 模式 — 通过 Command(goto=...) 切换
def handoff_to_expert(state):
    return Command(goto="expert_agent", graph=Command.PARENT)
```

> 完整多智能体代码 → `references/api-reference.md` §多智能体

---

## 关键 API

### 并行 Fan-out/Fan-in
```python
builder.add_edge(START, "worker_a")  # 多个节点
builder.add_edge(START, "worker_b")  # 同时从 START
builder.add_edge(START, "worker_c")  # 出发
builder.add_edge("worker_a", "aggregator")
builder.add_edge("worker_b", "aggregator")
builder.add_edge("worker_c", "aggregator")
```

### Reducer（并行汇聚）
```python
class State(TypedDict):
    results: Annotated[list, operator.add]  # 追加而非覆盖
```

### Checkpoint（持久化）
```python
from langgraph.checkpoint.sqlite import SqliteSaver
graph = builder.compile(checkpointer=SqliteSaver.from_conn_string("state.db"))
```

### 中断/恢复
```python
interrupt({"type": "review", "data": state["plan"]})  # 中断
graph.invoke(Command(resume={"approved": True}), config={"configurable": {"thread_id": "xxx"}})  # 恢复
```
