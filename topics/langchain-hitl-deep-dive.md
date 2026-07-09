# Human-in-the-Loop 深度剖析

> 从 LangGraph 中断原语到 DeepAgents 开箱即用：三层架构贯通 + 四种决策模式 + 企业风险分层
> 基于官方 4 文档 + 沧海九粟社区教程，2026-07-09 整理

---

## 一、一句话定位

**HITL = Agent 操作的安全门**。不是让 Agent 停下来问"你确定吗？"，而是在真正的危险操作（删文件、发邮件、调支付接口）执行前，插入人类审批——Agent 负责干活，人负责兜底。

| 对比维度 | 无 HITL | 有 HITL |
|----------|--------|--------|
| 删除文件 | Agent 直接删 | 暂停 → 人确认 → 删/不删 |
| 发送邮件 | Agent 直接发 | 暂停 → 人改收件人 → 发 |
| 调用付费 API | Agent 直接调 | 暂停 → 人审批 → 调/拒绝 |
| 执行部署 | Agent 直接部署 | 暂停 → 人 canary 验证 → 继续 |

---

## 二、HITL 三层架构全览

> **核心误解**：HITL 不是单一功能，而是 LangGraph → LangChain → DeepAgents **三层逐级封装**的能力栈。

### 2.1 三层关系图

```
┌─────────────────────────────────────────────────────────────┐
│  DeepAgents 应用层                                           │
│  interrupt_on={"delete_file": True}   ← 一行参数，开箱即用     │
│  内部自动装配 HumanInTheLoopMiddleware + PatchToolCalls        │
├─────────────────────────────────────────────────────────────┤
│  LangChain 中间件层                                           │
│  HumanInTheLoopMiddleware              ← 声明式工具级拦截       │
│  after_model 钩子 → 匹配工具 → interrupt() → Command(resume=)  │
├─────────────────────────────────────────────────────────────┤
│  LangGraph 运行时层                                           │
│  interrupt() 原语 + Command(resume=)   ← 节点内任意位置冻结     │
│  Checkpointer 持久化暂停状态             ← 基础设施             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 每层职责与边界

| 层次 | 控制粒度 | 使用方式 | 适用场景 |
|------|:--:|------|------|
| **LangGraph `interrupt()`** | 图中任意位置 | 在 node 函数内手动调用 `interrupt(some_value)` | 自定义工作流、非 Agent 场景 |
| **LangChain Middleware** | 工具级别 | `HumanInTheLoopMiddleware(interrupt_on={...})` | 用 `create_agent()` 的定制项目 |
| **DeepAgents `interrupt_on`** | 工具级别（声明式） | `create_deep_agent(interrupt_on={...})` | 90% 场景——开箱即用 |

### 2.3 选层决策表

| 你要做什么 | 用哪层 |
|-----------|--------|
| 用 DeepAgents，简单快速 | `interrupt_on` 参数 |
| 用 `create_agent()`，需要精确控制 | `HumanInTheLoopMiddleware` |
| 自定义 LangGraph 图，非 Agent 场景 | `interrupt()` 原语 |
| 需要在非工具操作处暂停（如节点间） | `interrupt()` 原语 |
| 需要静态断点调试 | `interrupt_before` / `interrupt_after` |

---

## 三、LangGraph 底层：`interrupt()` 机制（MDA）

### 3.1 核心思想

**在图的任意节点内动态"冻结"执行。** 不同于静态断点（`interrupt_before`/`interrupt_after` 在编译时固定），`interrupt()` 是动态的——可以放在 `if` 分支里、循环里、任何需要暂停的地方。

### 3.2 理论说明（静动分离）

```
════════════ 静态准备（图编译时） ════════════

① Checkpointer 配置（必须！中断恢复全靠它）
   │  MemorySaver — 开发用（内存，重启丢失）
   │  PostgresSaver — 生产用（数据库持久化）

② 图编译（声明节点 + 边）
   │  builder.add_node("approval", approval_node)
   │  builder.add_edge("approval", "next_node")

════════════ 动态执行（每次 invoke） ════════════

用户 invoke({"messages": [...]}, config={"thread_id": "x"})
  │
  ▼
approval_node 执行中...
  │
  ├── 正常业务逻辑...
  │
  ├── interrupt({"question": "确认删除？", "action": "delete_file"})
  │     │  ← 此时 LangGraph 抛出 GraphInterrupt 异常
  │     │  ← 运行时捕获异常 → 保存当前 state 到 Checkpointer
  │     │  ← 返回 interrupt 值给调用方
  │     │
  │     ▼
  │  调用方收到: {"__interrupt__": [{"question": "确认删除？", ...}]}
  │     │
  │     ▼
  │  人类决策 → Command(resume="approved")
  │     │  ← 运行时从 Checkpointer 恢复 state
  │     │  ← **整个 approval_node 从头重新执行！** ← 关键！
  │     │  ← 这次 interrupt() 返回 "approved"（而不是抛异常）
  │     │
  │     ▼
  │  node 继续执行后续逻辑...
  │
  ▼
下一节点...
```

**关键理解**：`interrupt()` 恢复时，**所在 node 从头重跑**——不是从 `interrupt()` 那一行继续。这就是为什么 5 条使用规则中第 1 条就是"不要在 `interrupt()` 前放非幂等副作用"。

### 3.3 关键代码骨架

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

class State(TypedDict):
    messages: list
    approved: bool

def approval_node(state: State):
    """需要人工审批的节点。"""
    # ① 检查是否已审批（恢复执行时 state.approved = True）
    if not state.get("approved"):
        # ② 暂停，等待人类决策
        decision = interrupt({"question": "确认执行此操作？"})
        # ③ 恢复后 decision = "approved" 或 "rejected"
        return {"approved": decision == "approved"}
    return {}

builder = StateGraph(State)
builder.add_node("approval", approval_node)
builder.add_edge(START, "approval")
builder.add_edge("approval", END)

graph = builder.compile(checkpointer=MemorySaver())  # ← 必须！

# 首次调用 — 触发中断
config = {"configurable": {"thread_id": "session-1"}}
result = graph.invoke({"messages": [], "approved": False}, config)

# 检查中断
if "__interrupt__" in result:
    for item in result["__interrupt__"]:
        print(f"需要审批: {item['question']}")

# 人类决策后恢复
graph.invoke(Command(resume="approved"), config)  # ← 同一 thread_id!
```

### 3.4 使用规则与反模式

> 来自官方 `langgraph-interrupts.md`，5 条硬规则。

| # | 规则 | 为什么 | ❌ 反模式 |
|---|------|--------|---------|
| ① | **不要在 `interrupt()` 前放非幂等副作用** | 恢复时 node 从头重跑，之前的副作用会被重复执行 | ❌ `send_email()` 然后 `interrupt()` |
| ② | **不要用 try/except 包裹 `interrupt()`** | 会被捕获导致 GraphInterrupt 无法传播到运行时 | ❌ `try: interrupt(...) except: pass` |
| ③ | **不要重排序 `interrupt()` 调用** | 多次中断时，运行时按顺序匹配 resume 值 | ❌ 第一次 `interrupt("a")` 后改代码为 `interrupt("b")` |
| ④ | **不要返回复杂值** | interrupt 值会被序列化，复杂对象可能失败 | ❌ `interrupt(lambda x: x)` |
| ⑤ | **Checkpointer 必须配置** | 没有 Checkpointer = 无法保存/恢复状态 | ❌ 忘记传 `checkpointer` |

**最佳实践**：把 `interrupt()` 放在 node 开头，所有副作用放在 `interrupt()` 返回之后：

```python
def safe_node(state):
    decision = interrupt({"action": "delete", "file": state["target"]})  # ← 先中断
    if decision == "approved":
        delete_file(state["target"])  # ← 副作用在中断之后
    return {}
```

---

## 四、LangChain 中间件层：`HumanInTheLoopMiddleware`（MDA）

### 4.1 核心思想

**声明式工具级拦截。** 你不需要写 node 和 `interrupt()`——告诉中间件"哪些工具需要审批"，它自动在工具调用前插入中断。Agent 的 `after_model` 钩子会检查模型输出的工具调用，匹配 `interrupt_on` 配置，触发 `interrupt()`。

### 4.2 理论说明（执行生命周期）

> 来自官方 `langchain-human-in-the-loop.md` §Execution lifecycle。

```
Agent invoke 开始
  │
  ▼
模型调用（LLM 生成响应 + 工具调用决策）
  │
  ▼
[HumanInTheLoopMiddleware.after_model 触发]  ← 关键钩子点
  │
  │  ① 检查模型输出的 tool_calls
  │  ② 与 interrupt_on 配置匹配
  │  ③ 匹配成功 → 构建 HITLRequest(action_requests=[...], review_configs={...})
  │  ④ 调用 interrupt(HITLRequest) → 暂停
  │
  ▼
[暂停] 返回 interrupt 给调用方
  │
  ▼
人类决策 → Command(resume={"decisions": [{...}, {...}]})
  │
  ▼
[恢复] 中间件处理 decisions:
  │  approve → 使用原始参数执行工具
  │  edit    → 使用修改后的参数执行工具
  │  reject  → 跳过工具，注入拒绝反馈到消息历史
  │  respond → 注入人类回复作为工具结果
  │
  ▼
Agent 继续执行（可能再次调模型，或直接返回）
```

**本质**：中间件 = `after_model` + `interrupt()` 的自动化封装。你不再手写 `interrupt()` 调用，而是声明"哪些工具需要审批"。

### 4.3 关键代码骨架

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

agent = create_agent(
    model="claude-sonnet-4-6",
    tools=[delete_file, send_email, read_file],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "delete_file": True,                                        # 完全中断
                "send_email": {"allowed_decisions": ["approve", "reject"]}, # 只能批/拒
                "read_file": False,                                         # 不中断
            },
        ),
    ],
    checkpointer=checkpointer,  # ← 必须！
)

# invoke → 遇到匹配的工具 → 中断
config = {"configurable": {"thread_id": "x"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "删除 /tmp/old.txt"}]},
    config=config,
    version="v2",  # HITL 必须 v2
)

# 检查中断
if hasattr(result, "interrupts") and result.interrupts:
    for action in result.interrupts:
        print(f"Agent 想调用 {action['name']}({action['arguments']})")

# 恢复
from langgraph.types import Command
agent.invoke(
    Command(resume={"decisions": [
        {"type": "approve"},
    ]}),
    config=config,
    version="v2",
)
```

---

## 五、DeepAgents 应用层：`interrupt_on`（MDA）

### 5.1 核心思想

**一行参数 = 完整 HITL。** DeepAgents 把 LangChain 中间件的配置提升为 `create_deep_agent()` 的参数——传 `interrupt_on={...}` 自动装配 `HumanInTheLoopMiddleware` + `PatchToolCallsMiddleware`（修复中断造成的消息历史断裂）。

### 5.2 三种配置值语义

| 配置值 | 行为 | 示例 |
|--------|------|------|
| `True` | 完全中断，允许全部 4 种决策 | `"delete_file": True` |
| `False` | 不中断，Agent 自动执行 | `"read_file": False` |
| `{"allowed_decisions": [...]}` | 中断，但只允许指定决策类型 | `"send_email": {"allowed_decisions": ["approve", "reject"]}` |

### 5.3 与下层的关系

```python
# DeepAgents 帮你做的：
agent = create_deep_agent(model=model, tools=[...], interrupt_on={"x": True})

# 等价于 create_agent() 手动装配：
agent = create_agent(
    model=model, tools=[...],
    middleware=[
        # ... DeepAgents 常驻层中间件 ...
        HumanInTheLoopMiddleware(interrupt_on={"x": True}),
        PatchToolCallsMiddleware(),  # 修复中断后的消息历史
    ],
)
```

> 不需要 HITL？不传 `interrupt_on` 即可——中间件不会装配，零开销。

---

## 六、四种决策模式深度剖析（MDA）

### 6.1 核心思想

四种决策 = 四种人机交互意图。不是所有暂停都是"是否继续"——有时是"帮我改个参数"，有时是"我问你个问题"。

### 6.2 逐项详解

| 决策 | 发生了什么 | 工具是否执行 | Agent 看到什么 |
|------|-----------|:--:|------|
| `approve` | 使用 Agent 原始参数执行工具 | ✅ 是 | 正常的 ToolMessage（工具返回值） |
| `edit` | 使用人类修改后的参数执行工具 | ✅ 是（改参） | ToolMessage（用修改后的参数调用的结果） |
| `reject` | 跳过工具调用，注入反馈 | ❌ 否 | ToolMessage(content=拒绝原因) |
| `respond` | 不执行工具，人类回复作为工具结果 | ❌ 否 | ToolMessage(content=人类回复) |

**reject vs respond 的核心区别**：

| 场景 | 用 | 原因 |
|------|:--:|------|
| 不要删除这个文件 | `reject` | Agent 需要知道"工具没执行 + 为什么" |
| 不要发这封邮件 | `reject` | 副作用操作被拒绝 |
| "客户邮箱是什么？"（ask_user 工具） | `respond` | 工具本身就是"问人"的设计 |
| "帮我翻译这段文本"（ask_user 工具） | `respond` | 人代替工具回答问题 |

> ⚠️ **`respond` 的内容被模型当作成功的 ToolMessage**——对删除/发送/部署等副作用工具，必须用 `reject`。

### 6.3 前后端完整链路

```
前端                                    后端
────                                    ────
                                        Agent 调用 send_email(to="a@x.com")
                                        HumanInTheLoopMiddleware 中断
                                        ← {interrupts: [{name: "send_email",
                                          arguments: {to: "a@x.com"}}]}

useStream 检测到 interrupts →
渲染 ApprovalCard:
  [Approve] [Edit to] [Reject] [Respond]

用户点 [Edit]，改为 "b@x.com" →
                                        → Command(resume={decisions: [
                                          {type: "edit", args: {to: "b@x.com"}}
                                        ]})
                                        中间件用 b@x.com 执行 send_email
                                        → ToolMessage("邮件已发送到 b@x.com")
                                        Agent 继续...
```

---

## 七、条件中断与风险分层

### 7.1 `when` 谓词：三种写法模式

> 需要 `langchain>=1.3.3`。

**模式 A — 基于参数值判断**：

```python
def writes_outside_workspace(request: ToolCallRequest) -> bool:
    path = request.tool_call["args"].get("file_path", "")
    return not path.startswith("/workspace/")

interrupt_on = {
    "write_file": {
        "allowed_decisions": ["approve", "reject"],
        "when": writes_outside_workspace,
    },
}
```

**模式 B — 基于 State 动态判断**：

```python
def user_is_new(request: ToolCallRequest) -> bool:
    return request.state.get("user_role") == "new_user"
```

**模式 C — 组合判断**：

```python
def high_value_transfer(request: ToolCallRequest) -> bool:
    amount = request.tool_call["args"].get("amount", 0)
    currency = request.tool_call["args"].get("currency", "CNY")
    return amount > 10000 or currency not in ["CNY", "USD"]
```

### 7.2 四级风险分层

| 级别 | 工具示例 | 策略 | HITL 配置 |
|:--:|------|------|------|
| 🟢 低风险 | `read_file`, `grep`, `search` | 不中断 | `False` |
| 🟡 中风险 | `write_file`, `edit_file` | 条件中断 | `{"allowed_decisions": ["approve", "reject"], "when": ...}` |
| 🔴 高风险 | `delete_file`, `send_email`, `execute_shell`, `deploy` | 始终中断 | `True`（全部 4 种决策） |
| ⚫ 财务/合规 | `transfer_funds`, `approve_contract` | 仅批/拒（不可改参） | `{"allowed_decisions": ["approve", "reject"]}` |

### 7.3 企业场景对照

| 行业 | 🟢 不中断 | 🟡 条件中断 | 🔴 始终中断 | ⚫ 仅批/拒 |
|------|----------|------------|------------|----------|
| 金融 | 查余额 | 修改报告 | 发起转账 | 批准贷款 |
| 医疗 | 查药品信息 | 更新病历 | 开处方 | 手术审批 |
| 内容审核 | 读取评论 | 标记可疑 | 删除内容 | 封禁账号 |
| DevOps | 查看日志 | 修改配置 | 重启服务 | 数据库迁移 |

---

## 八、子Agent HITL 编排

### 8.1 继承 vs 覆盖 vs 独立策略

```python
agent = create_deep_agent(
    model=model,
    tools=[delete_file, read_file],
    interrupt_on={
        "delete_file": True,
        "read_file": False,          # 主 Agent 读文件不需要审批
    },
    subagents=[{
        "name": "file-manager",
        "description": "管理文件操作",
        "system_prompt": "你是文件管理助手。",
        "tools": [delete_file, read_file],
        interrupt_on={
            "delete_file": True,
            "read_file": True,       # 子 Agent 读文件也要审批！更严格
        }
    }],
    checkpointer=checkpointer,
)
```

**继承规则表**：

| 场景 | 效果 |
|------|------|
| 子 Agent 不配置 `interrupt_on` | 继承主 Agent 的全部 HITL 配置 |
| 子 Agent 配置了 `interrupt_on` | **完全覆盖**主 Agent 的 HITL（不合并） |
| 子 Agent 想禁用一个主 Agent 的中断项 | 显式设 `"tool_name": False` |

### 8.2 多 Agent 中断协调

- **批量工具调用**：一次模型调用触发多个工具时，`interrupt_on` 匹配的第一个触发中断，已通过的非中断工具仍会执行
- **子 Agent 中断**：子 Agent 的中断对主 Agent 透明——主 Agent 只看到子 Agent 回来了一个结果
- **主 Agent 恢复**：子 Agent 中断恢复后，继续执行直到返回给主 Agent

---

## 九、流式场景 HITL

### 9.1 `stream()` 中的中断检测

```python
config = {"configurable": {"thread_id": "x"}}

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "删除 /tmp/log.txt"}]},
    stream_mode=["updates", "messages"],
    config=config,
    version="v2",
):
    # 检查是否有中断
    if hasattr(chunk, "interrupts") and chunk.interrupts:
        for action in chunk.interrupts:
            print(f"需要审批：{action['name']}({action['arguments']})")
        break  # 暂停流，等人类决策

# ... 人类决策后 ...
for chunk in agent.stream(
    Command(resume={"decisions": [{"type": "approve"}]}),
    stream_mode=["updates", "messages"],
    config=config,
    version="v2",
):
    print(chunk)  # 继续流式输出
```

### 9.2 批量工具调用的中断处理

Agent 一次模型调用可能发出多个工具调用（如 4 个并行的 `write_file`）。中断逻辑：

1. `interrupt_on` 匹配第一个触发项 → 中断
2. 非中断工具（`False`）已在中断前执行完毕
3. 恢复后，未执行的工具继续执行

---

## 十、调试与排障

### 10.1 LangSmith Studio 中断视图

在 LangSmith Studio 中调试 HITL：

1. 静态断点（`interrupt_before` / `interrupt_after`）→ Studio 会在节点前后自动暂停
2. 动态 `interrupt()` → Studio 显示中断值和等待状态
3. 可以在 Studio 中手动输入 resume 值继续执行

### 10.2 常见故障与定位

| 症状 | 原因 | 解决方案 |
|------|------|---------|
| 中断后恢复失败 | `thread_id` 不一致 | 确保 invoke 使用相同的 `config` |
| 恢复后状态不对 | node 从头重跑，副作用重复 | 把副作用移到 `interrupt()` 返回之后 |
| `interrupt` 不触发 | 缺少 `version="v2"` | DeepAgents/LangChain HITL 必须 v2 |
| 批量工具只有一个被中断 | 设计如此：匹配第一个触发 | 给所有危险工具都加 `interrupt_on` |
| 决策顺序错乱 | `decisions` 与 `action_requests` 顺序不匹配 | 严格一一对应 |
| 恢复后 Agent 不继续 | 未传入新消息或 `Command` 格式错误 | 检查 `Command(resume={"decisions": [...]})` |

---

## 十一、快速速查

### 11.1 配置速查

```
中断一个工具：  interrupt_on={"tool_name": True}
不中断：       interrupt_on={"tool_name": False}
限制决策类型：  interrupt_on={"tool_name": {"allowed_decisions": ["approve", "reject"]}}
条件中断：      interrupt_on={"tool_name": {"allowed_decisions": [...], "when": my_func}}
子Agent独立：  subagents=[{"name":..., "interrupt_on": {...}}]
```

### 11.2 决策类型速查

```
approve  → 批准，原样执行
edit     → 修改参数后执行
reject   → 不执行，告知 Agent 原因（副作用工具必须用此）
respond  → 不执行，人类回复作为工具结果（仅用于"问用户"类工具）
```

### 11.3 故障速查

```
中断不触发 → 检查 version="v2"
恢复失败   → 检查 thread_id 一致
副作用重复 → 把副作用移到 interrupt() 之后
决策不生效 → 检查 decisions 与 action_requests 一一对应
```

---

## 参考资料

> 专题报告引用规范见 [`topics/INDEX.md`](INDEX.md#扩展规则)。

### 本地源文件

| 本地路径 | 官方 URL |
|----------|----------|
| `docs/official/langgraph/langgraph-interrupts.md` | [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) |
| `docs/official/langchain/langchain-human-in-the-loop.md` | [LangChain HITL](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) |
| `docs/official/langchain/langchain-frontend-human-in-the-loop.md` | [Frontend HITL](https://docs.langchain.com/oss/python/langchain/frontend-human-in-the-loop) |
| `docs/official/deepagents/deepagents-human-in-the-loop.md` | [DeepAgents HITL](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop) |
| `docs/community/沧海九粟/ch09-human-in-the-loop.md` | 沧海九粟社区《Deep Agents 实战》第 9 章 |

### 交叉引用

| 本地专题 | 关联内容 |
|----------|---------|
| `topics/langchain-middleware-deep-dive.md` §3.3/§3.6 | HITL 作为安全护栏内置中间件 + DeepAgents 条件层自动激活 |
| `skills/langchain-v1-suite/deepagents-v1/SKILL.md` §5 | interrupt_on 参数完整用法 + 风险分层 |

> **整理日期**: 2026-07-09
