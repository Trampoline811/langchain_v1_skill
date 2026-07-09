# LangChain 多智能体架构 · 速查手册

> 4 种官方模式的横向对比：Skills / Subagents / Handoffs / Router
> 基于 LangChain 官方多智能体系列教程，2026-07-02 整理

---

## 一、一句话定位

| 模式 | 一句话 | 隐喻 |
|------|--------|------|
| **Skills** | 一个 Agent，按需加载专业知识和提示词 | 🎒 瑞士军刀 — 一把刀，换不同的附件 |
| **Subagents** | 主管协调多个专业子 Agent，子 Agent 不直接面对用户 | 🏢 经理派活 — 经理接需求，分给专家执行 |
| **Handoffs** | 单 Agent 按工作流步骤切换配置，状态驱动流转 | 🏭 流水线 — 一个工位干完，传下一个工位 |
| **Router** | 分类后并行分发到多个专业 Agent，结果汇总合成 | 📮 分拣中心 — 一封信来了，同时抄送多个部门 |

---

## 二、架构图（文字版）

```
Skills:                          Subagents:
  User                            User
   │                               │
   ▼                               ▼
  Agent ◄── middleware ──┐        Supervisor
   │                     │          │
   ├─ load_skill(SQL)    │          ├─ call_calendar_agent()
   ├─ load_skill(Python) │          ├─ call_email_agent()
   └─ ...                 │          └─ call_research_agent()
   (同一Agent，不同prompt)  │               │
                          │          ┌───────┴───────┐
  Skills存储在文件/DB中 ──┘          ▼               ▼
                               Calendar Agent   Email Agent
                               (子Agent不直接面对User)

Handoffs:                       Router:
  User                            User
   │                               │
   ▼                               ▼
  Agent (step: triage)            Classifier
   │ record_warranty()             │
   ▼ (Command→state change)       ├─→ GitHub Agent ──┐
  Agent (step: classifier)        ├─→ Notion Agent ──┤
   │ record_issue()               └─→ Slack Agent ───┤
   ▼ (Command→state change)                           ▼
  Agent (step: specialist)                       Synthesizer
   │ provide_solution()                              │
   ▼                                                 ▼
  User                                              User
```

---

## 三、核心机制对比

| 维度 | Skills | Subagents | Handoffs | Router |
|------|--------|-----------|----------|--------|
| **Agent 数量** | 1 个 | N+1 个（主管+子） | 1 个（多配置） | N+2 个（分类+领域+合成） |
| **核心 API** | Middleware + `@tool` | `create_agent()` → `@tool` 包装 | Middleware + `Command` + State | `StateGraph` + `Send` |
| **状态管理** | 可选 custom state | Checkpointer (主管) | **必须** custom state + checkpointer | StateGraph 内建 state |
| **提示词策略** | 渐进披露（先摘要后全文） | 每个子 Agent 独立 system prompt | 每步骤独立 system prompt | 每领域 Agent 独立 prompt |
| **工具策略** | 共享工具 + 技能专属工具 | 每个子 Agent 注册自己工具 | 每步骤不同工具集 | 每领域 Agent 注册自己工具 |
| **并行能力** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐⭐⭐ |
| **多跳能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — |
| **直接用户交互** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **分布式开发** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐ |

---

## 四、各模式详解

### 4.1 Skills — 按需技能加载

**代表教程**: Build a SQL assistant with on-demand skills

**核心思想**: 技能的**渐进披露**（Progressive Disclosure）——Agent 启动时只看到技能摘要，需要时才加载完整提示词。类似 `llms.txt` 的设计理念：先给目录，按需取正文。遵循 [Agent Skills 规范](https://agentskills.io/specification)。

> **想深入理解中间件机制？** 这里只做横向对比。中间件的静态准备⇄动态执行时序、常见误解纠正，见 [`topics/langchain-skills-deep-dive.md` §五](langchain-skills-deep-dive.md#五langchain-multi-agent-skillsdiy-模式)。

**理论说明**:

Skills 模式的核心机制链：**工具调用 → 中间件拦截 → 动态提示词注入**。

| 机制 | 作用 | LangChain 实现 |
|------|------|----------------|
| 技能定义与发现 | Agent 知道有哪些技能可用，但不加载全文 | `@tool` 定义 `load_skill(name)`，Agent 主动探寻调用 |
| 动态提示词注入 | 每次模型调用前，将技能摘要注入 system prompt | `AgentMiddleware.wrap_model_call` 包裹模型调用，拼装提示词 |
| 渐进披露 | 先暴露 description（~100 tokens），按需 read_file 正文 | `SKILLS` dict 存 description + prompt，工具调用时才返回全文 |
| 状态约束（高级） | 确保 Agent 加载技能后才能使用对应工具 | `CustomState` 跟踪 `skills_loaded`，受限工具检查 state |

**运行时串联流程**：

```
1. 启动 → SkillMiddleware.wrap_model_call 被触发
   → 遍历所有 SKILL 的 description → 拼成摘要注入 system prompt
   → Agent 此时知道："我有 sales_analytics 和 inventory_management 两个技能"

2. 用户："帮我写个查询上月销冠的 SQL"
   → Agent 判断匹配 sales_analytics 技能
   → Agent 主动调用 load_skill("sales_analytics")
   → 工具返回完整的 schema + 业务规则 prompt

3. 后续对话中 Agent 加载了完整技能知识 → 写出正确的 SQL
   → 如有写 SQL 的受限工具，检查 state.skills_loaded → 放行
```

**本质**：`@tool` 让 Agent 主动探寻 + `wrap_model_call` 动态拼装提示词 = 按需知识注入。不是改代码，是改 Agent "看到的"上下文。

**关键代码骨架**:
```python
# 1. 技能定义
SKILLS = {
    "sales_analytics": {
        "description": "Write SQL queries for sales data",
        "prompt": "You are a sales SQL expert. Tables: orders(id, amount, date)...",
    },
}

# 2. 加载工具
@tool
def load_skill(skill_name: str) -> str:
    """Load a skill's full instructions by name."""
    skill = SKILLS.get(skill_name)
    if not skill:
        return f"Skill '{skill_name}' not found. Available: {list(SKILLS.keys())}"
    return skill["prompt"]

# 3. 中间件
class SkillMiddleware(AgentMiddleware):
    tools = [load_skill]
    
    def wrap_model_call(self, request, handler):
        skills_prompt = "\n".join(
            f"- {name}: {s['description']}" for name, s in SKILLS.items()
        )
        new_system = request.system_prompt + f"\n\nAvailable skills:\n{skills_prompt}"
        return handler(request.override(system_prompt=new_system))

# 4. 创建
agent = create_agent(model, middleware=[SkillMiddleware()])
```

**高级扩展**: 约束控制
- 自定义 `CustomState`，跟踪已加载技能
- 受限工具（写 SQL）检查 state.skills_loaded，未加载时拒绝执行
- 确保 Agent 必须先 `load_skill` 才能使用领域工具

**优点**:
- 上下文极省：不加载不用的技能，大量技能也不会撑爆 context window
- 单 Agent 简单：没有多 Agent 协调的复杂度
- 集中控制：始终是一个 Agent 在对话，用户体验一致
- 独立开发：技能文件独立维护，不同团队可各自管理
- 与 DeepAgents 原生集成

**缺点**:
- 无真正并行：同一时刻只能用一个技能（不过单 Agent 可一次加载多个）
- 不能直接用户交互切换：技能切换靠 Agent 判断，无外部控制
- 依赖 Agent 判断何时加载技能，可能不加载或加载错误

**适用场景**:
- 大型知识库系统（许多领域，按需取用）
- SQL/BigQuery 助手（多数据库/多 schema）
- 工具丰富的 Agent（避免一次暴露所有工具描述）
- 多团队维护各自领域知识的场景

---

### 4.2 Subagents — 主管-子Agent 协调

**代表教程**: Build a personal assistant with subagents

**核心思想**: 一个 Supervisor Agent 通过工具调用派发任务给专业子 Agent。子 Agent 只返回结果，不直接面对用户。**所有路由经过主管**——用户感觉在和"一个全能助手"对话，但后台有专家团队并行工作。

**理论说明**:

Subagents 模式的核心机制链：**Agent 实例化 → 工具封装 → 主管调度 → 多跳串联**。

| 机制 | 作用 | LangChain 实现 |
|------|------|----------------|
| 独立子 Agent | 每个子 Agent 有独立的 system_prompt + tools + context window | `create_agent(model, tools=[...], system_prompt="你是XX专家")` |
| Agent-as-Tool | 把子 Agent 包装为主管可调用的工具 | `@tool` 函数内嵌 `subagent.invoke({"messages": [...]})` |
| 集中路由 | 主管 LLM 动态决策调用哪些子 Agent，支持单跳或多跳 | Supervisor 也是 `create_agent()`，持有所有子 Agent 工具 |
| 上下文工程 | 控制子 Agent 接收什么输入、主管读到什么输出 | 输入：query only vs full context；输出：result only vs full history |
| HITL（可选） | 子 Agent 执行前暂停等用户批准 | `interrupt()` 在子 Agent 调用前插入 |

**运行时串联流程**：

```
1. 用户："帮我安排明天下午的会议，然后发邮件通知参会人"
   → Supervisor 分析 → 这是两个关联任务，先日历后邮件

2. Supervisor 调用 call_calendar_agent("明天下午3点创建会议")
   → @tool 内部 invoke calendar_agent
   → 子 Agent 用自己的 prompt + tools 独立运行 → 返回会议创建结果

3. Supervisor 读取结果（会议ID、时间、参会人）
   → 调用 call_email_agent("通知张三、李四明天下午3点开会")
   → @tool 内部 invoke email_agent → 返回邮件发送结果

4. Supervisor 汇总两个结果 → "已创建明天下午3点的会议并通知参会人"
```

**本质**：Agent-as-Tool — 子 Agent 被封装为工具函数，Supervisor 的 LLM 做动态路由决策。这是"子任务有依赖（先A后B）"场景的天然解决方案——Supervisor 读 A 的结果，决定如何调 B。

**关键代码骨架**:
```python
# 1. 创建子 Agent
calendar_agent = create_agent(
    model,
    tools=[create_event, list_events, delete_event],
    system_prompt="You are a calendar assistant. Manage user's schedule.",
)

# 2. 包装为工具
@tool("calendar", description="Manage calendar: create/list/delete events")
def call_calendar_agent(query: str) -> str:
    result = calendar_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

# 3. 创建主管
supervisor = create_agent(
    model,
    tools=[call_calendar_agent, call_email_agent, call_research_agent],
    system_prompt="You are a personal assistant. Delegate tasks to specialists.",
    checkpointer=InMemorySaver(),
)
```

**设计决策矩阵**:
| 决策点 | 选项 A | 选项 B |
|--------|--------|--------|
| 同步/异步 | Sync（等子Agent完成）— 默认 | Async（后台执行）— 复杂 |
| 工具模式 | Tool per agent（一Agent一工具）| Single dispatch（一个task工具+参数选Agent）|
| 子Agent发现 | System prompt 枚举 | Enum 约束 | Tool-based 动态发现 |
| 子Agent输入 | Query only（仅用户问题）| Full context（带对话历史）|
| 子Agent输出 | Result only（仅最后消息）| Full history（完整对话记录）|

**优点**:
- 真正的并行：主管可同时调用多个子 Agent
- 多跳串联：先查日历，根据结果再调邮件 Agent
- 模块化：子 Agent 独立开发/测试/部署
- 灵活路由：LLM 动态决策而非硬编码规则
- HITL 可在子Agent层面插入
- **CompiledSubAgent**：可复用现成 LangGraph 图作为子 Agent（`CompiledSubAgent(name="...", runnable=graph)`）
- **结构化输出**：子 Agent 可通过 `response_format=PydanticModel` 返回 JSON（`>=0.5.3`），避免返回大量原始数据

**缺点**:
- 调用开销：每次子Agent调用多一层 LLM 调用（one-shot 场景比 Handoffs/Skills 多 1 次）
- 子 Agent 无直接用户交互（需额外 interrupt 处理）
- 上下文工程复杂：需考虑输入/输出/发现的组合策略
- Supervisor 可能选错子 Agent

**适用场景**:
- 个人助手（日历 + 邮件 + 搜索）
- 多领域研究（Web搜索 + 代码分析 + 论文检索）
- 复杂工作流（串联多个专业Agent）
- 需要并行加速的场景

---

### 4.3 Handoffs — 状态驱动工作流流转

**代表教程**: Build customer support with handoffs

**核心思想**: **一个 Agent，多套配置**——通过状态字段驱动中间件动态切换 system prompt 和工具集。用户感觉在和"不同的人"对话（分流→专员→解决），但始终是同一个 Agent。适合有明确步骤的业务流程。

**理论说明**:

Handoffs 模式的核心机制链：**状态定义 → 工具触发流转 → 中间件动态配置 → 角色切换**。

| 机制 | 作用 | LangChain 实现 |
|------|------|----------------|
| 状态机 | `current_step` 字段是状态机核心，决定 Agent 当前扮演哪个角色 | `TypedDict` 定义 State Schema，含 `current_step` + 业务字段 |
| 工具触发流转 | 工具执行业务逻辑后，通过 Command 更新状态，驱动下一步 | `Command(update={"current_step": "next_step", ...})` |
| 中间件动态配置 | 每次模型调用前，读 `current_step` → 切换对应 prompt + tools | `AgentMiddleware.wrap_model_call` 读 `request.state` → 查配置表 |
| 跨轮持久化 | 状态必须跨对话轮次保持，否则步骤信息丢失 | `checkpointer=InMemorySaver()`（生产用 PostgresSaver） |

**运行时串联流程**：

```
1. 用户："我的设备坏了" → Agent 启动，current_step="triage"
   → Middleware.wrap_model_call 读 step → 应用分流配置
   → system_prompt="收集保修信息" + tools=[record_warranty_status]

2. Agent 询问保修状态 → 用户回答"在保"
   → Agent 调用 record_warranty_status("in_warranty")
   → 工具返回 Command(update={"current_step": "issue_classifier", "warranty_status": "in_warranty"})

3. 下一轮模型调用 → Middleware 检测 current_step 变更
   → 切换配置：system_prompt="分类问题类型" + tools=[record_issue_type]
   → 用户看到的是"分类专员"在提问，但实际是同一个 Agent

4. 步骤单向流转（分流→分类→解决→升级）→ 直到结束
   → 必要时可实现回退："go back to triage"
```

**本质**：状态机驱动 + `wrap_model_call` 动态配置 = 单 Agent 模拟多角色无缝切换。工具不止做业务——它同时是"步骤流转触发器"。

**关键代码骨架**:
```python
# 1. 状态
class SupportState(TypedDict):
    current_step: str  # "triage" | "issue_classifier" | "resolution_specialist"
    warranty_status: str | None
    issue_type: str | None

# 2. 工具（带状态转移）
@tool
def record_warranty_status(status: Literal["in_warranty", "out_of_warranty"],
                           runtime: ToolRuntime[None, SupportState]) -> Command:
    return Command(update={
        "messages": [ToolMessage(content=f"Warranty: {status}", tool_call_id=runtime.tool_call_id)],
        "warranty_status": status,
        "current_step": "issue_classifier",  # ← 步骤转移
    })

# 3. 步骤配置
STEP_CONFIGS = {
    "triage": {
        "prompt": "Collect warranty info. Ask if under warranty.",
        "tools": [record_warranty_status],
    },
    "issue_classifier": {
        "prompt": "Classify the issue as hardware or software.",
        "tools": [record_issue_type],
    },
    "resolution_specialist": {
        "prompt": "Provide solution. Escalate if needed.",
        "tools": [provide_solution, escalate_to_human],
    },
}

# 4. 中间件
class ApplyStepConfig(AgentMiddleware):
    state_schema = SupportState
    
    def wrap_model_call(self, request, handler):
        step = request.state.get("current_step", "triage")
        config = STEP_CONFIGS[step]
        return handler(request.override(
            system_prompt=config["prompt"],
            tools=config["tools"],
        ))

# 5. 创建
agent = create_agent(
    model,
    tools=all_tools,
    state_schema=SupportState,
    middleware=[ApplyStepConfig()],
    checkpointer=InMemorySaver(),  # ← 必须，跨轮保持状态
)
```

**两种实现方式**:
| 方式 | 复杂度 | 适用场景 |
|------|--------|----------|
| **单 Agent + Middleware**（教程方式）| 低 | 大多数 handoff 场景 ⭐推荐 |
| **多 Agent Subgraph** | 高 | 每个节点需要独立的复杂图（含检索/反思等） |

**优点**:
- 步骤清晰：显式的工作流状态机，行为可预测
- 直接用户交互：每个步骤都可以与用户对话
- 上下文管理好：每步只加载当前需要的 prompt 和工具
- 单Agent简单：无需协调多个Agent实例
- 支持回退/跳转：可实现"返回上一步"等灵活流转

**缺点**:
- 不支持并行：同一时刻只能在一个步骤
- 硬编码流转：步骤在 `Command` 中写死，不如 LLM 灵活
- 复杂流程状态爆炸：步骤多了状态管理复杂
- 需要 checkpointer：跨轮必须持久化

**适用场景**:
- 客服工单流程（收集信息→分类→解决→升级）
- 多步骤表单填写
- 审批工作流
- 任何有明确阶段/步骤的业务流程

---

### 4.4 Router — 分类→并行分发→合成

**代表教程**: Build a multi-source knowledge base with routing

**核心思想**: 一个**无状态**的分类器 + **并行**专业 Agent + 结果合成器。用户问一个问题，系统同时查多个来源，汇总后给出连贯答案。适合"一个问题需要多个知识源才能回答"的场景。

**理论说明**:

Router 模式的核心机制链：**图编排 → 分类分发 → 并行扇出 → 结果归并 → 合成**。

> **注意**：Router 是唯一不在 `create_agent()` 内实现的模式——它用 LangGraph `StateGraph` 做图编排，每个节点可以是 Agent 或普通函数。

| 机制 | 作用 | LangChain 实现 |
|------|------|----------------|
| 图编排 | 定义节点、边、条件分支的拓扑结构 | `StateGraph(RouterState)` 构建 DAG |
| 分类分发 | 分析 query，决定路由到哪些领域 | Classifier 节点（LLM call 或规则）→ 输出 domains list |
| 并行扇出 | 对每个 domain 同时发起查询，延迟 = max(各节点) | `Send(domain, state)` 对每个 domain 创建并行任务 |
| 结果归并 | 多个并行节点同时写入 state，无竞态合并 | `Annotated[dict, reducer_merge]` — reducer 函数自动合并 |
| 合成 | 阅读所有领域答案，生成连贯最终回答 | Synthesizer 节点（一次 LLM call） |

**运行时串联流程**：

```
1. 用户："LangGraph 的 checkpointer 怎么配置？"
   → Classifier 分析 → domains = ["github", "notion", "slack"]

2. route_to_domains 用 Send API 并行扇出：
   ├─ github_agent 搜索 GitHub 文档 → "checkpointer 用 PostgresSaver..."
   ├─ notion_agent 搜索 Notion → "checkpointer 配置示例..."
   └─ slack_agent 搜索 Slack 历史 → "相关讨论：持久化最佳实践..."

3. 三个 Agent 同时运行 → 各自结果写入 state.answers
   → Reducer（reducer_merge）自动合并：{github: "...", notion: "...", slack: "..."}

4. Synthesizer 检测到所有结果已归并（图结构保证）
   → 阅读汇总 → "配置 checkpointer 需要三步：1) PostgresSaver 连接..."
```

**本质**：图编排 + `Send` 并行扇出 + `reducer` 归并 = 一次查询同时搜 N 个源。这是"子任务之间没有依赖关系"场景的最优解——全并行，延迟只取决于最慢的那个。

**关键代码骨架**:
```python
from langgraph.graph import StateGraph, Send
from langgraph.types import Command

# 1. 状态
class RouterState(TypedDict):
    query: str
    domains: list[str]
    answers: Annotated[dict, reducer_merge]  # ← reducer 合并并行结果
    final_answer: str

# 2. 分类器
def classifier(state: RouterState):
    """分析查询，决定路由到哪些领域"""
    result = router_llm.invoke(f"Which domains to search? {state['query']}")
    domains = parse_domains(result)  # ["github", "notion"]
    return {"domains": domains}

# 3. 领域 Agent
def github_agent(state: RouterState):
    """搜索 GitHub 文档"""
    result = github_search(state["query"])
    return {"answers": {"github": result}}

def notion_agent(state: RouterState):
    return {"answers": {"notion": notion_search(state["query"])}}

# 4. 并行分发
def route_to_domains(state: RouterState):
    """用 Send 对每个 domain 创建一个并行任务"""
    return [Send(domain, state) for domain in state["domains"]]

# 5. 合成器
def synthesizer(state: RouterState):
    """阅读所有领域答案，生成最终回答"""
    all_answers = "\n".join(f"[{k}]: {v}" for k, v in state["answers"].items())
    result = synthesis_model.invoke(f"Query: {state['query']}\nAnswers:\n{all_answers}")
    return {"final_answer": result}

# 6. 构建图
builder = StateGraph(RouterState)
builder.add_node("classifier", classifier)
builder.add_node("github_agent", github_agent)
builder.add_node("notion_agent", notion_agent)
builder.add_node("synthesizer", synthesizer)
builder.add_edge(START, "classifier")
builder.add_conditional_edges("classifier", route_to_domains, ["github_agent", "notion_agent"])
builder.add_edge("github_agent", "synthesizer")
builder.add_edge("notion_agent", "synthesizer")
builder.add_edge("synthesizer", END)
workflow = builder.compile()
```

**Stateless vs Stateful Router**:
| 类型 | 机制 | 适用 |
|------|------|------|
| Stateless（教程默认）| 每次请求独立，无记忆 | 搜索/问答，单轮 |
| Stateful: Tool Wrapper | 包装为 `@tool`，由对话 Agent 调用 | 简单，推荐 |
| Stateful: Full Persistence | Router 本身加 checkpointer | 复杂多轮路由 |

**优点**:
- 真正的并行：多个领域同时搜索，延迟 = max(各Agent耗时)
- 模块化：每个领域 Agent 独立开发和维护
- 结果合成：专门的合成步骤提供连贯答案
- 确定性路由：分类逻辑可控（可用规则或简单 LLM call）
- 适合固定领域集合

**缺点**:
- 不支持多跳：Router 是一次性分发，不能串联（先查A→根据A结果查B）
- 无状态（默认）：每一轮独立，不记上下文（可通过 stateful 解决）
- 图复杂度：对简单任务来说过重
- 领域硬编码：添加新领域需要改图结构

**适用场景**:
- 多源知识库搜索（GitHub + Notion + Slack + ...）
- RAG 多源检索
- 多语言翻译路由
- 多模型路由（便宜模型做简单任务，强模型做复杂任务）

---

## 五、性能对比

### 5.1 模型调用次数

| 场景 | Subagents | Handoffs | Skills | Router |
|------|:---------:|:--------:|:------:|:------:|
| **单次简单请求** ("买咖啡") | 4 次 | 3 次 ✅ | 3 次 ✅ | 3 次 ✅ |
| **重复请求**（第二次相同） | 8 次 (4+4) | 5 次 (3+2) ✅ | 5 次 (3+2) ✅ | 6 次 (3+3) |
| **多领域请求** | 5 次, 9K tokens ✅ | 7+ 次, 14K+ tokens | 3 次, 15K tokens | 5 次, 9K tokens ✅ |

### 5.2 优化建议

| 优化目标 | 推荐模式 |
|----------|----------|
| 单次请求最快 | Handoffs / Skills / Router |
| 重复请求最省 | Handoffs / Skills |
| 并行执行 | Subagents / Router |
| 大上下文领域 | Subagents / Router |
| 简单聚焦任务 | Skills |

---

## 六、选用决策树

```
需要多个Agent并行工作？
  ├─ 是 → 需要灵活的多跳串联？
  │        ├─ 是 → Subagents
  │        └─ 否 → Router
  └─ 否 → 有明确的多步骤工作流？
           ├─ 是，步骤有先后顺序 → Handoffs
           └─ 否，按需加载不同知识 → Skills

不确定？用这个视角：
  - 用户感觉在和"不同的人"对话 → Handoffs
  - 用户感觉在和"一个全能助手"对话，后台有专家团队 → Subagents  
  - 用户感觉在和"一个专家"对话，专家会翻书查资料 → Skills
  - 用户问一个问题，系统同时查多个来源 → Router
```

---

## 七、组合模式

> 4 种模式**可以混用**。官方明确推荐的组合：

| 组合 | 示例 |
|------|------|
| Subagents + Skills | 主管调用子Agent，子Agent内部用Skills按需加载知识 |
| Subagents + Router | 主管的工具之一是 Router（多源搜索） |
| Handoffs + Skills | 客服某个步骤加载对应的技能（如退款政策Skill） |
| Router + Stateful Wrapper | Router 包装为 Agent 工具，Agent 维护对话上下文 |

---

## 八、记忆口诀

```
Skills    — 一个脑子，多本手册，用时翻
Subagents — 一个老板，多个专家，派活干
Handoffs  — 一条流水线，多个工位，往下传
Router    — 一个分拣员，多个部门，同时查
```

---

## 九、快速选型表

| 你的情况 | 选这个 |
|----------|--------|
| 我有很多领域知识，不想一次塞进 prompt | **Skills** |
| 我需要灵活的任务分解，LLM 动态决定找谁 | **Subagents** |
| 我有明确的业务流程步骤（1→2→3） | **Handoffs** |
| 我有多个独立数据源，需要同时查询 | **Router** |
| 我只想写最简单的代码 | **Skills**（单 Agent 最简单） |
| 我需要最快的并行查询 | **Router**（Send 真并行） |
| 我需要在步骤间保持用户对话连续性 | **Handoffs** |
| 我的子任务之间没有依赖关系 | **Router**（并行） |
| 我的子任务之间有依赖（先A后B） | **Subagents**（多跳） |

---

## 参考资料

> 专题报告引用规范见 [`topics/INDEX.md`](INDEX.md#扩展规则)。

### 本地源文件

| 本地路径 | 官方 URL |
|----------|----------|
| `docs/official/langchain/langchain-multi-agent-index.md` | [Multi-agent overview](https://docs.langchain.com/oss/python/langchain/multi-agent) |
| `docs/official/langchain/langchain-multi-agent-skills.md` | [Skills pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/skills) |
| `docs/official/langchain/langchain-multi-agent-skills-sql-assistant.md` | [Skills: SQL assistant](https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant) |
| `docs/official/langchain/langchain-multi-agent-subagents.md` | [Subagents pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents) |
| `docs/official/langchain/langchain-multi-agent-subagents-personal-assistant.md` | [Subagents: Personal assistant](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant) |
| `docs/official/langchain/langchain-multi-agent-handoffs.md` | [Handoffs pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs) |
| `docs/official/langchain/langchain-multi-agent-handoffs-customer-support.md` | [Handoffs: Customer support](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs-customer-support) |
| `docs/official/langchain/langchain-multi-agent-router.md` | [Router pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/router) |
| `docs/official/langchain/langchain-multi-agent-router-knowledge-base.md` | [Router: Knowledge base](https://docs.langchain.com/oss/python/langchain/multi-agent/router-knowledge-base) |

> **整理日期**: 2026-07-02
