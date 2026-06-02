# 选型决策指南

> 专门回答"我的 RAG pipeline 要不要引入 LangChain/LangGraph"这类问题。

## LCEL 在 v1.0 的定位

**LCEL（`|` 管道语法）在 v1.0 中不再是核心概念。**

- 技术上仍可用（底层 Runnable 协议保留，`model | prompt | parser` 仍然能跑）
- 但官方文档几乎不再提 LCEL，推荐做法是 `create_agent()` 或直接 `model.invoke()`
- LCEL 解决的是"怎么串组件"——旧版 chain 的核心问题。v1 的答案不同：不需要串，Agent 自己决定调用顺序

```
旧版 LCEL 思维:  retriever | prompt | model | parser   ← 你规定顺序
v1 思维:          create_agent(model, tools=[retriever]) ← Agent 决定顺序
```

唯一保留 LCEL 的场景：非 Agent 的简单分类流水线（`text | model`），但 `model.invoke()` 也够。

## v1.0 稳定性

| 问题            | 答案                                                       |
| --------------- | ---------------------------------------------------------- |
| 版本策略        | **LTS（长期支持）**，遵循 SemVer                     |
| LangChain v1    | 当前稳定版（2025.11 发布）                                 |
| LangGraph v1    | 当前稳定版，API 与 v0.x 几乎不变                           |
| v0.3 状态       | MAINTENANCE 模式，支持到**2026年12月**（仅安全补丁） |
| Breaking change | v1 承诺不破坏 API。将来 v2 发布后，v1 继续 LTS 支持        |
| Python 要求     | 3.10+                                                      |

**对生产系统的含义：** 不像 v0.x 时代每半年一次大地震。现在引入 LangGraph v1，至少 2 年内不会有 breaking change。

## 纯 Python vs LangGraph 边界速查

| 需求                           |         用 LangGraph         |        用纯 Python        |
| ------------------------------ | :--------------------------: | :-----------------------: |
| 线性批处理（无分支/循环/并行） |                              |            ✅            |
| 简单 if/else 分流              |                              |            ✅            |
| LLM 分类 + 路由到不同路径      |  ✅ Router 模式，白盒可审计  |                          |
| 多路并行执行 + 结果汇聚        |    ✅ Send API / Fan-out    | 需手动 ThreadPoolExecutor |
| 子任务依赖管理                 |     ✅ 图拓扑 = 依赖声明     |        需手动管理        |
| 中间状态持久化（故障恢复）     |      ✅ checkpoint 自动      |       需手动序列化       |
| 人工审核断点                   | ✅`Command(interrupt=...)` |      需自建中断机制      |
| 答案质量迭代循环               |    ✅ Evaluator-Optimizer    |       需手动 while       |
| 动态决定下一步（Agent）        |     ✅`create_agent()`     |     纯 Python 做不到     |

**原则：** 复杂分支用 LangGraph，简单线性用纯 Python。不是替代，是补充。

## 何时引入 LangGraph

### 不要用 LangGraph 的场景

| 场景                                   | 为什么                               | 用纯 Python                              |
| -------------------------------------- | ------------------------------------ | ---------------------------------------- |
| 线性批处理（parse→chunk→ingest）     | 没有条件分支、没有循环、没有并行需求 | `a(); b(); c()` 足够                   |
| 简单查询（retrieve→rerank→generate） | 控制流是 if/else 就够                | `if simple: fast_path else: slow_path` |
| 已有成熟的纯 Python pipeline           | 框架只会增加调试成本                 | 保持现状                                 |

### 值得用 LangGraph 的场景

| 场景                                      | LangGraph 的价值                                                        |
| ----------------------------------------- | ----------------------------------------------------------------------- |
| 复杂查询分解（multi-step query planning） | 图的拓扑 = 硬约束执行计划；每个 state transition 可记录、可回放、可审计 |
| 多路并行检索+汇聚                         | 无依赖节点天然并行（如招行+建行数据同时查）                             |
| 需要人工审核断点                          | checkpoint 机制天然支持中断→审核→继续                                 |
| 需要故障恢复                              | 每一步自动持久化，崩溃后可从断点恢复                                    |
| 动态路由                                  | 条件边让 LLM 决定下一步走哪个节点，白盒可审计                           |

### 推荐模式："图在模块内"（Graph-in-a-Module）

不是整个 pipeline 换框架，而是在 C.1 模块内部嵌入一个小的 StateGraph：

```
generation/query_planner.py          ← 新增模块
  ├── 内部使用 LangGraph StateGraph
  │   nodes:  [classify, decompose, route, execute, synthesize]
  │   edges:  classify → {simple: route, complex: decompose → execute → synthesize}
  │   state:  {question, plan[], sub_results[], final_answer}
  │
  └── 对外暴露简单接口
      planner.plan(question) → ExecutionPlan
      planner.execute(plan)  → FinalAnswer

generation/questions_processing.py   ← 现有模块，调用 query_planner
  process_question(question, schema):
      plan = self.planner.plan(question)
      if plan.is_simple:
          return self._fast_path(question)   ← 当前 C.1 逻辑，不变
      else:
          return self.planner.execute(plan)  ← LangGraph 执行 DAG
```

对外部调用者来说接口完全不变——`process_question()` 还是返回 `answer_dict`。

## LangGraph 的最小依赖

```bash
pip install langgraph        # StateGraph, checkpoint, Command — 不依赖 langchain
pip install langchain-core   # 可选：BaseMessage, ToolMessage 等基础类型
# langchain 不需要安装      # create_agent, middleware 在 langchain 包里
```

如果只做查询规划 DAG（不需要 Agent 自主决策），只装 `langgraph` 即可。StateGraph 的节点可以是纯 Python 函数，不需要 LLM。

## checkpoint 用于金融审计断点

```python
from langgraph.checkpoint.memory import InMemorySaver  # 或 SqliteSaver/PostgresSaver
from langgraph.types import Command

# 图在关键步骤自动持久化 state
graph = builder.compile(checkpointer=SqliteSaver.from_conn_string("audit.db"))

# 中断：在需要审核的节点返回 Command(interrupt=...)
def audit_step(state):
    return Command(interrupt={"action": "review_required", "data": state["plan"]})

# 恢复：审核通过后
graph.invoke(Command(resume={"approved": True}), config=config)

# 审计：每个 state transition 已持久化到 SQLite，可查询、可回放
```

结合 `HumanInTheLoopMiddleware` 也可以实现，但金融场景建议用 StateGraph 裸写——更白盒、更容易定制审计逻辑。
