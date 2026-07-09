# LangChain Skills 机制深度剖析

> Skills 的两种实现路径、渐进披露原理、文件规范、扩展模式、与 Tools/Memory 的边界
> 基于 LangChain 官方 multi-agent/skills + deepagents/skills + 源码分析，2026-07-02 整理

---

## 一、一句话定位

**Skills = Agent 的按需"知识插件"**。不是工具（Tools），不是记忆（Memory），而是**打包好的领域指令 + 可选执行代码**。Agent 启动时只看到摘要，需要时才加载全文——这叫**渐进披露（Progressive Disclosure）**。

| 对比维度 | Skills | Tools | Memory |
|----------|--------|-------|--------|
| **本质** | Markdown 指令 + 可选脚本 | Python/JS 函数 | JSON 数据 |
| **触发方式** | Agent 读 description 后主动 `read_file` | Agent 根据 function schema 调用 | 按需读写 Store |
| **加载时机** | 按需（渐进披露） | 每次 model call 注入 schema | 调用时读写 |
| **适合存放** | 领域知识、工作流指南 | 外部 API 调用、计算 | 用户偏好、跨会话状态 |
| **持久化** | 文件系统（`/skills/` 目录） | 代码 | Store |

---

## 二、两种实现路径

LangChain 生态中，Skills 有**两层实现**，容易混淆：

```
┌─────────────────────────────────────────────────────────┐
│  LangChain Multi-Agent Skills（模式层）                      │
│  自己实现 — Middleware + @tool + load_skill               │
│  教程：SQL Assistant                                      │
│  对应文档：langchain/multi-agent/skills                    │
├─────────────────────────────────────────────────────────┤
│  DeepAgents Skills（内置层）                                 │
│  开箱即用 — SkillsMiddleware，create_deep_agent(skills=[...]) │
│  额外能力：Interpreter Skills、沙箱执行、权限控制               │
│  对应文档：deepagents/skills                               │
└─────────────────────────────────────────────────────────┘
```

**关系**：
- DeepAgents Skills 是 LangChain Skills 模式的**内置实现**
- 两者都遵循 [Agent Skills 规范](https://agentskills.io/specification)
- 两者都遵循 `llms.txt` 的渐进披露设计理念
- LangChain 模式层 → 灵活，你需要自己搭
- DeepAgents 内置层 → 方便，传个路径就完事

---

## 三、Skill 文件规范

### 3.1 目录结构

```
skills/
├── langgraph-docs/              # 一个 skill = 一个目录
│   └── SKILL.md                 # 必需！入口文件
│
├── arxiv-search/
│   ├── SKILL.md
│   ├── scripts/                  # 可执行脚本
│   │   └── search.py
│   └── references/               # 参考文档
│       └── api-guide.md
│
└── order-helpers/
    ├── SKILL.md
    └── assets/                   # 静态资源
        └── template.json
```

### 3.2 SKILL.md 模板

```markdown
---
name: langgraph-docs
description: Use this skill for requests related to LangGraph.
---

# langgraph-docs

## Overview
This skill explains how to access LangGraph documentation...

## Instructions
### 1. Fetch the documentation index
Use `fetch_url` to read: https://docs.langchain.com/llms.txt

### 2. Select relevant documentation
Based on the question, identify 2-4 most relevant URLs...

### 3. Fetch and synthesize
Read the selected URLs and synthesize an answer...
```

### 3.3 Frontmatter 字段

| 字段 | 必须 | 说明 |
|------|:--:|------|
| `name` | ✅ | 技能唯一标识 |
| `description` | ✅ | **决定 Agent 是否使用该技能的关键**。Agent 仅基于此字段做匹配判断 |
| `module` | ❌ | Interpreter Skill 专用。指向可导入的 Python/TS 文件路径 |

> **关键设计**：Agent 决定是否使用某个 Skill 时，**只看 `description`**。写出清晰、具体的 description 是 Skills 效果的核心。

---

## 四、渐进披露（Progressive Disclosure）机制

### 4.1 三步流程

```
Agent 启动
  │
  ├─ 读取所有 SKILL.md 的 frontmatter（仅 name + description）
  │  → 注入 System Prompt："Skills System" 区块
  │  → 此时 Agent 只知道技能列表，不知道详细内容
  │
  ▼
用户提问
  │
  ▼
Step 1 — 匹配（Match）
  Agent 遍历技能 description，判断哪些技能匹配当前任务
  │
  ▼
Step 2 — 读取（Read）
  Agent 调用 read_file 读取匹配的 SKILL.md 完整内容
  │
  ▼
Step 3 — 执行（Execute）
  Agent 按技能指令操作，需要时访问 scripts/ references/ assets/
```

### 4.2 为什么不用 Context Window 全装？

| 全部加载 | 渐进披露 |
|----------|----------|
| 100 个 Skill → ~500K tokens 一次性吃满上下文 | 100 个 Skill → 启动只占 ~5K tokens（描述摘要） |
| 超出上下文窗口直接崩溃 | 理论上可支持无限多个 Skill |
| 不需要 Agent 判断，但成本极高 | Agent 需要判断何时加载，但上下文极省 |

### 4.3 Agent 看到的 System Prompt 注入

DeepAgents 自动注入的 "Skills System" 区块示例：

```
## Skills System

You have access to the following skills. Match the user's request 
to the most relevant skill(s), then read the full SKILL.md file.

Available skills:
- langgraph-docs (path: /skills/langgraph-docs/SKILL.md)
  Use this skill for requests related to LangGraph.
- arxiv-search (path: /skills/arxiv-search/SKILL.md)
  Search and retrieve academic papers from arxiv.
```

Agent 匹配后调用 `read_file("/skills/langgraph-docs/SKILL.md")` 获取完整指令。

---

## 五、LangChain Multi-Agent Skills（DIY 模式）

### 5.1 核心思想与理论说明

**核心思想**：用 LangChain 原生的 `@tool` + `AgentMiddleware` 手动实现渐进披露。遵循 [Agent Skills 规范](https://agentskills.io/specification)，与 DeepAgents 内置版同源异构。

**常见误解**（对照纠正）：

| 你可能以为... | 实际情况 |
|-------------|---------|
| 中间件在"最后一次"调模型前修改提示词 | 中间件在**每一次**调模型前都触发 |
| 中间件把 skill 全文注入 system prompt | 中间件注入**摘要**（description），全文由 `load_skill` 工具返回值进入对话历史 |
| `SkillMiddleware` 是 LangChain 内置的 | 教程里是自己手写的——`class SkillMiddleware(AgentMiddleware)` |

**静态⇄动态分离**：

```
════════════ 静态准备（程序启动，跑一次） ════════════

① SKILLS: list[Skill]                数据层：所有技能的定义
   │  name: "sales_analytics"          ├─ description → 摘要，注入 system prompt
   │  description: "写销售SQL"           └─ content    → 全文，load_skill 按需返回
   │  content: "## 表结构\n..."

② load_skill @tool                   工具层：让 Agent 能"主动探寻"技能
   │  def load_skill(name):           遍历 SKILLS → 返回 content 全文
   │      return skill["content"]

③ class SkillMiddleware(AgentMiddleware):  中间件层：拦截每一次模型调用
   │  tools = [load_skill]                  注册工具 + 注入摘要
   │  def wrap_model_call(request, handler):
   │      request.system_prompt += skills_summary  ← 每次调模型前拼上摘要
   │      return handler(request)

④ agent = create_agent(model,        组装：装上中间件
        middleware=[SkillMiddleware()])

════════════ 动态执行（每次用户请求） ════════════

用户: "帮我写查询上月销冠的SQL"
  │
  ▼
[SkillMiddleware.wrap_model_call 第1次触发]  ← 注意：每次调模型都跑！
  │  修改 system_prompt: "...\n可用技能:\n- sales_analytics: 写销售SQL\n- inventory_management: 写库存SQL"
  │
  ▼
模型看到: system_prompt(含摘要) + 用户问题 + 工具列表(含 load_skill)
模型判断: "我需要 sales_analytics 的完整 schema" → 调用 load_skill("sales_analytics")
  │
  ▼
load_skill 执行: 遍历 SKILLS → 匹配 name → return content 全文(~2000 tokens)
  │  全文作为 ToolMessage 进入对话历史
  │
  ▼
[SkillMiddleware.wrap_model_call 第2次触发]  ← 再次注入摘要（每次模型调用都跑）
  │
  ▼
模型看到: system_prompt(含摘要) + 对话历史(含完整 schema) + 用户问题
模型现在有完整 DB 结构 → 写出正确 SQL
  │
  ▼
(高级) write_sql_query 检查 state.skills_loaded → 放行
```

**本质（一行口诀）**：`@tool` 让 Agent 主动探寻 + `wrap_model_call` 每次拦截注入摘要 = 按需知识注入。

**掌握深度建议**：记住"静态准备三样东西（数据 + 工具 + 中间件），动态两步流程（Agent 看摘要选 skill → 调工具取全文）"。`TypedDict` vs `Pydantic`、`content_blocks` 的具体格式是实现细节，自己写的时候再查。

> **常见疑问：为什么 `tools = [load_skill]` 写在中间件类上，而不是 `create_agent(tools=[...])` 里？**
>
> 两种写法效果完全一样——Agent 最终都能拿到 `load_skill` 工具。区别在**打包习惯**：
>
> ```python
> # 写法A：直接传 create_agent
> agent = create_agent(model, tools=[load_skill], middleware=[SkillMiddleware()])
>
> # 写法B：写在中间件类变量上（教程选这个）
> class SkillMiddleware(AgentMiddleware):
>     tools = [load_skill]
> agent = create_agent(model, middleware=[SkillMiddleware()])
> ```
>
> 教程选 B 是因为 `load_skill` 和 `SkillMiddleware` 逻辑上是一体的——中间件管注入摘要，工具管按需返回全文。写在一起，复制 `SkillMiddleware` 到别的项目时工具自动跟过去。**不是技术必须，是组织整洁。** 如果你的工具和中间件没有逻辑归属关系（如通用搜索工具），直接传 `create_agent(tools=[...])` 就行。

### 5.2 核心架构

```
┌──────────┐     ┌─────────────────┐     ┌──────────────┐
│   User    │────→│     Agent       │────→│  SKILLS 存储  │
│           │     │                 │     │  (文件/DB)    │
└──────────┘     │ system_prompt:  │     └──────────────┘
                 │ "可用技能:       │
                 │  - sales: SQL销售│
                 │  - inventory: 库存│
                 │                 │
                 │ tools:          │
                 │ - load_skill()  │──→ 加载完整 prompt
                 │ - write_sql()   │
                 │                 │
                 │ middleware:     │
                 │ SkillMiddleware │──→ 注入技能摘要到 system prompt
                 └─────────────────┘
```

### 5.3 关键代码骨架

**Step 1 — 定义技能**

```python
SKILLS = {
    "sales_analytics": {
        "description": "Write SQL queries for sales data",
        "prompt": """You are a sales SQL expert.
Database: orders(id, customer_id, amount, date, status)
Key metrics: revenue, churn, LTV, conversion rate.
Common queries: sales by month, top customers, trend analysis.""",
    },
    "inventory_management": {
        "description": "Write SQL queries for inventory data",
        "prompt": """You are an inventory SQL expert.
Database: products(id, name, stock, warehouse_id, last_restock)
Key metrics: turnover rate, stockout risk, dead stock.
Common queries: low stock alerts, reorder recommendations.""",
    },
}
```

**Step 2 — 创建加载工具**

```python
from langchain.tools import tool

@tool
def load_skill(skill_name: str) -> str:
    """Load a skill's full instructions by name."""
    skill = SKILLS.get(skill_name)
    if not skill:
        available = ", ".join(SKILLS.keys())
        return f"Skill '{skill_name}' not found. Available: {available}"
    return skill["prompt"]
```

**Step 3 — 构建中间件**

```python
from langchain.agents.middleware import AgentMiddleware

class SkillMiddleware(AgentMiddleware):
    """注入技能摘要到 system prompt。"""
    tools = [load_skill]  # 注册技能加载工具

    def wrap_model_call(self, request, handler):
        skills_prompt = "\n".join(
            f"- {name}: {s['description']}"
            for name, s in SKILLS.items()
        )
        new_system = (
            request.system_prompt
            + f"\n\nAvailable skills (use load_skill to get full instructions):\n{skills_prompt}"
        )
        return handler(request.override(system_prompt=new_system))
```

**Step 4 — 创建 Agent**

```python
from langchain.agents import create_agent

agent = create_agent(
    model,
    system_prompt="You are a SQL query assistant.",
    middleware=[SkillMiddleware()],
)
```

### 5.4 高级：带约束的状态控制

**核心思想**：工具自己检查 Agent 是否"有资格"调用它——不是靠 prompt 劝，而是程序化硬拦截。

**理论说明（静动分离）**：

```
════════════ 静态准备 ════════════

① CustomState(TypedDict)             状态层：加 skills_loaded 字段
   │  skills_loaded: list[str]             跟踪"Agent 读过哪些 skill"

② @tool 中读 runtime.state           守卫层：工具被调用时先检查
   │  if "sales_analytics" not in loaded:     未授权 → 返回 Error
   │      return "Error: Load ... first"        已授权 → 放行

③ SkillMiddleware(AgentMiddleware[CustomState]):
   │  state_schema = CustomState       中间件层：声明状态扩展
   │  tools = [load_skill, write_sql_query, ...]

════════════ 动态执行 ════════════

用户: "写个查询上月销冠的 SQL"
  │
  ▼
Agent 没加载 skill → 直接调 write_sql_query("SELECT ...")
  │
  ▼
write_sql_query 执行 → runtime.state.get("skills_loaded") → []
  → "sales_analytics" not in [] → return "Error: Load 'sales_analytics' skill first"
  │
  ▼
Agent 收到拒绝 → 被迫先调 load_skill("sales_analytics") → skills_loaded = ["sales_analytics"]
  │
  ▼
Agent 再次调 write_sql_query → skills_loaded 中有 "sales_analytics" → 放行 ✅
```

**本质（一行口诀）**：`state_schema` 扩展状态 + 工具内读 `runtime.state` 守卫判断 = 技能级访问控制。

**应用场景**：

| 场景 | 为什么需要 |
|------|-----------|
| 多技能 Agent，技能间有边界 | 库存 skill 的工具不该在只加载了销售 skill 时被调用——表结构完全不同 |
| 合规/审计要求 | 发邮件、删数据、调支付接口等敏感操作——必须确认 Agent 已读安全策略 skill |
| 多步骤工作流 | 强制顺序：load_skill → 查数据 → 写报告，跳步就报错 |
| 开发调试 | 快速发现 Agent "跳过思考直接行动"的坏习惯 |

> **与 §9.4 坑点② 的关系**：`allowed-tools` 字段只是 prompt 文本建议（"请勿吸烟"贴纸），这里才是真正的程序化硬拦截（烟雾报警器）。

加载 skill 后才能使用对应工具：

```python
class CustomState(TypedDict):
    skills_loaded: list[str]  # 跟踪已加载的技能

@tool
def write_sql_query(query: str, runtime: ToolRuntime[None, CustomState]) -> str:
    """Write and validate a SQL query. Requires skill to be loaded first."""
    loaded = runtime.state.get("skills_loaded", [])
    if "sales_analytics" not in loaded:
        return "Error: Load 'sales_analytics' skill first before writing SQL."
    # ... 执行查询逻辑

class SkillMiddleware(AgentMiddleware[CustomState]):
    state_schema = CustomState
    tools = [load_skill, write_sql_query]
    # ... wrap_model_call 同上
```

---

## 六、DeepAgents Skills（内置模式）

### 6.0 核心思想与理论说明

**核心思想**：DIY 模式的"全自动封装"——`create_deep_agent(skills=[...])`，传路径即用。把 §五的 60 行样板代码压缩成了一行参数。

**与 DIY 的对应关系**（"你手写的那些，内置版帮你干了什么"）：

```
DIY（§五）                             内置（§六）
═══════════                           ═══════════
① SKILLS: list[Skill] 手动定义    →  自动扫描 /skills/ 目录下所有 SKILL.md
② @tool load_skill 手写           →  Agent 直接用 read_file 读 SKILL.md（文件系统中已有的能力）
③ class SkillMiddleware 手写      →  SkillsMiddleware（deepagents 内置，from deepagents.middleware import）
④ wrap_model_call 手写注入        →  自动通过三模板插槽注入 "Skills System" 区块
⑤ create_agent(middleware=[...])  →  create_deep_agent(skills=[...]) 一行搞定
```

**静态⇄动态分离**：

```
════════════ 静态准备（create_deep_agent 调用时，跑一次） ════════════

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    skills=["/skills/main/", "/skills/research/"],  ← 传路径即可！
)

SkillsMiddleware 启动：
  ① 扫描 /skills/main/ 和 /skills/research/ 下所有 SKILL.md
  ② 解析每个 SKILL.md 的 YAML frontmatter → 提取 {name, description, path}
  ③ 组装三模板插槽：
     {skills_locations}  → "/skills/main/, /skills/research/"
     {skills_list}       → "- langgraph-docs: LangGraph 相关\n- arxiv-search: 论文检索"
     {skills_load_warnings} → ""（无警告时为空）
  ④ 拼入 system prompt 的 "Skills System" 区块
  ⑤ 检查 state.skills_metadata：如果已存在（来自上轮对话/checkpoint）→ 跳过加载（去重）

════════════ 动态执行（每次用户请求） ════════════

用户: "LangGraph 的 checkpointer 怎么配置？"
  │
  ▼
Agent 启动时的 system_prompt 中已有：
  ## Skills System
  - langgraph-docs (path: /skills/langgraph-docs/SKILL.md)
    Use this skill for LangGraph-related questions.
  - arxiv-search (path: /skills/arxiv-search/SKILL.md)
    Search academic papers.
  │
  ▼
Agent 判断匹配 → 调用 read_file("/skills/langgraph-docs/SKILL.md")
  │  注意：这里不是 load_skill @tool！是通用的 read_file，因为 SkillsMiddleware 已经配了文件系统
  │
  ▼
Agent 读到完整 SKILL.md → 按指令行动
  │
  ▼
(可选) SKILL.md 有 module: scripts/helper.py
  → Agent 代码中 import skills.langgraph_docs.scripts.helper → 调确定性函数
  │
  ▼
(可选) sandbox=True → 技能脚本在隔离沙箱运行 → pip install / 跑 shell
```

**本质（一行口诀）**：DIY 的"自动挡"——你不再手写三样东西，传个路径就自动完成扫描→注入→读取全流程。

**掌握深度建议**：理解"内置版 = DIY 的自动封装"这个对应关系即可。三模板插槽的具体语法、`CompositeBackend` 的路由配置是高级主题，需要时再查。

### 6.1 DIY vs 内置 选型速查

| 需求 | 选 |
|------|-----|
| 只想快速用，不想写样板代码 | **内置** `create_deep_agent(skills=[...])` |
| 需要 Skill 提供可导入 Python 函数 | **内置** Interpreter Skills |
| 需要沙箱隔离执行 | **内置** Sandbox |
| 已有 LangChain 项目，不想引入 deepagents 依赖 | **DIY** `Middleware + @tool` |
| 需要完全自定义技能存储/加载逻辑 | **DIY** |
| 团队只用 LangChain 不用 DeepAgents | **DIY** |

### 6.2 一行启用

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    skills=["/skills/main/", "/skills/research/"],
)
```

底层自动装配 `SkillsMiddleware`，无需手动写 `load_skill` 工具和自定义中间件。

### 6.3 SkillsMiddleware 参数

```python
from deepagents.middleware import SkillsMiddleware
from deepagents.backends import StateBackend

SkillsMiddleware(
    backend=StateBackend(),      # 文件后端（State/Filesystem/Store/CompositeBackend）
    sources=["./skills/"],       # 技能源路径列表
    sandbox=True,                # 技能代码在隔离沙箱中执行
)
```

### 6.4 Source Precedence（源优先级）

同一 skill 名出现在多个源时，**后列者覆盖前列者**（last wins）：

```python
# 如果 /skills/user/ 和 /skills/project/ 都有 "web-search"
# → /skills/project/ 的版本胜出
agent = create_deep_agent(
    skills=["/skills/user/", "/skills/project/"],
)
```

这允许**分层覆盖**：用户自定义 skill 覆盖项目默认 skill。

### 6.5 运行时动态加载

除了固定列表，还支持动态回调：

```python
# 固定列表
skills=["/skills/common/"]

# 动态回调 — 按用户/环境切换
def resolve_skills(runtime):
    user_id = runtime.context.user_id
    if user_id in vip_users:
        return ["/skills/common/", "/skills/vip/"]
    return ["/skills/common/"]

agent = create_deep_agent(skills=resolve_skills)
```

### 6.6 Interpreter Skills（可执行技能）

DeepAgents 独有的能力：Skill 不仅是指令，还可以**提供可导入的 Python 函数**。

**适用场景**：
- 可复用的解析器/打分器/校验器（需要确定性行为，不能让 LLM 临时生成）
- 太细节的算法逻辑（不宜放 prompt）
- 需要在工作流中多次调用的辅助函数

**用法** — 在 SKILL.md frontmatter 加 `module` 字段：

```markdown
---
name: score-calculator
description: Calculate relevance scores for search results
module: scripts/scorer.py       # ← 关键！指向可导入模块
---

# Score Calculator

## Usage
```python
from skills.score_calculator import calculate_score
results = calculate_score(query, documents)
```
```

Agent 在执行代码时可以直接 `import` 这些模块，行为**确定、可测试**。

### 6.7 Sandbox 执行

```python
SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],
    sandbox=True,  # skill 脚本在隔离沙箱中运行
)
```

沙箱环境提供 Shell 访问、依赖安装、CLI 调用能力。需要在生产环境配置 Sandbox Backend。

### 6.8 技能权限（Skill Permissions）

DeepAgents 支持按 Skill 粒度控制文件访问权限：

- 不同 Skill 可以有不同的文件读写范围
- 子 Agent 的 Skill 权限完全隔离

---

## 七、Skills + Subagents 协同

DeepAgents 中 Skills 与 Subagents 的继承规则：

```
create_deep_agent(
    skills=["/skills/main/"],     # 主 Agent + GP 子 Agent 自动继承
    subagents=[
        {                          # 自定义子 Agent 不继承
            "name": "researcher",
            "skills": ["/skills/research/"],  # 只用自己的 skills
        },
    ],
)
```

| Agent 类型 | Skills 来源 | `system_prompt` | `tools` | `model` |
|------------|------------|:--:|:--:|:--:|
| 主 Agent | `create_deep_agent(skills=...)` 直接注入 | 自定义 | 自定义 + 继承 | 自定义 |
| General-purpose 子 Agent | **自动继承**主 Agent 的 skills | ❌ 不继承 | ✅ 默认继承 | ✅ 默认继承 |
| 自定义子 Agent | **不继承**，需显式传 `skills=[...]` | ❌ 不继承 | ✅ 默认继承 | ✅ 默认继承 |
| 子 Agent 之间 | **完全隔离**，互不可见 | — | — | — |

> **关键区别**：`system_prompt` 始终不继承（子 Agent 需独立定义角色），`tools` 和 `model` 默认继承主 Agent（指定后完全替换，不合并）。

**三种后端加载 Skills 的方式：**

| 后端 | 代码 | 适用场景 |
|------|------|---------|
| **StateBackend** | `SkillsMiddleware(backend=StateBackend(), sources=["./skills/"])` | 默认、开发调试 |
| **StoreBackend** | `SkillsMiddleware(backend=StoreBackend(namespace=...), sources=[...])` | 跨会话持久、企业知识库 |
| **FilesystemBackend** | `SkillsMiddleware(backend=FilesystemBackend(root_dir="..."), sources=[...])` | 本地文件、CLI 工具 |

**Skills 权限分层模型**（`permissions` 参数）：

| 权限类型 | 含义 | 场景 |
|---------|------|------|
| `{"type": "shared", "users": "*"}` | 全员共享 | 通用知识技能 |
| `{"type": "limited", "users": ["admin"]}` | 限定用户 | 管理员专属 |
| `{"type": "read_only"}` | 只读保护 | 合规/安全策略 |
| `{"type": "editable", "scope": "user"}` | 用户可编辑 | 个人笔记/偏好 |

---

## 八、三种扩展模式

官方列出三种在 DIY 实现中可扩展的方向：

### 8.1 动态工具注册

加载 Skill 时间不仅注入 prompt，还**动态注册新工具**：

```
load_skill("database_admin")
  → 注入 DBA 领域 prompt
  → 动态注册 backup_database / restore_database / migrate_schema 工具
```

利用 `Command(update={"tools": [...]})` 实现。

### 8.2 层级技能（Hierarchical Skills）

Skills 可以形成树状结构：

```
data_science/               # 父技能
├── SKILL.md                # 入口："需要数据科学帮助时加载我"
├── pandas_expert/          # 子技能
│   └── SKILL.md
├── visualization/          # 子技能
│   └── SKILL.md
└── statistical_analysis/   # 子技能
    └── SKILL.md
```

Agent 先加载 `data_science` → 根据具体需求再加载子技能 → 逐级深入。

### 8.3 引用感知（Reference Awareness）

Skill prompt 中不嵌入全部参考内容，而是**告知参考文件的位置和使用时机**：

```markdown
# sales-analytics SKILL.md

## References
- `references/schema.md` — Full table schemas. Read when writing queries.
- `references/business_rules.md` — Business logic. Read for metric definitions.
- `references/examples.md` — Example queries. Read for query patterns.
```

Agent 按需 `read_file`，进一步节省上下文。

---

## 九、生产环境考量

### 9.1 中间件装配顺序

DeepAgents 中推荐的标准 middleware 栈：

```python
agent = create_agent(
    model=model,
    tools=[search],
    middleware=[
        FilesystemMiddleware(backend=backend),       # 文件读写能力
        SummarizationMiddleware(model=model, backend=backend),  # 历史压缩
        MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),  # 长期记忆
        SkillsMiddleware(backend=backend, sources=["./skills/"]),    # 技能加载
    ],
)
```

### 9.2 与沙箱的集成

当 skills 存储在 StoreBackend 但代码要在 Sandbox 执行时，需要自定义 middleware：

```python
class SkillsSandboxMiddleware(AgentMiddleware):
    """在 before_agent 中将 skill 脚本同步到沙箱文件系统。"""

    async def before_agent(self, state, runtime):
        # 从 Store 读取所有 skill 文件
        skill_files = await read_skills_from_store(runtime)
        # 上传到沙箱
        for path, content in skill_files.items():
            await runtime.sandbox.upload(path, content)
```

### 9.3 性能数据

| 场景 | Skills 调用次数 |
|------|:---:|
| 单次简单请求 | 3 次 model call |
| 重复请求（再次相同任务） | 5 次 (3+2) ✅ |
| 多领域请求 | 3 次, 15K tokens |

> Skills 在多领域场景下调用次数最少（3 次），但 token 量较高（15K — 因为加载了 skill 完整 prompt）。

### 9.4 已知坑点与避坑指南

> 以下 5 个坑点来自社区反馈、GitHub Issues 和官方评估数据，经 deep-research 对抗验证确认。

| # | 坑点 | 严重度 | 现状 | 避坑建议 |
|---|------|:---:|------|----------|
| ① | **并行子 Agent 并发冲突**：`skillsMetadata` 字段遗漏于 `EXCLUDED_STATE_KEYS`，多个子 Agent 并行完成时触发 `InvalidUpdateError` | 🔴 高 | ✅ 已修复（2026.1） | 升级到最新 deepagents，使用 `StateSchema + ReducedValue` 自定义 reducer |
| ② | **`allowed-tools` 无实效**：SKILL.md 的 `allowed-tools` 字段仅渲染为系统提示中的文本行，**不做任何程序化拦截**。Agent 仍可调用绑定工具集中的任何工具 | 🟡 中 | ⚠️ 已知限制 | 不要把安全策略依赖于此字段；需要真正工具隔离时，在子 Agent 层面限制 `tools` 参数 |
| ③ | **Skill 调用可靠性 ~70%**：即使显式提示调用某个 skill，成功率也不到 100%。Claude Code 在某些任务中"从未调用相关 skill" | 🟡 中 | ⚠️ 已知限制 | 在 `AGENTS.md`/`CLAUDE.md` 中预置调用指引，不要仅依赖 skill description。对关键任务在 system prompt 中显式要求 |
| ④ | **Skill 数量 > 12 精度下降**：模型选择正确 skill 的精度显著下降。~20 个时频繁选错，~12 个时恢复一致正确 | 🟡 中 | ⚠️ 设计约束 | 合并小 skill 为更少但更大的单元；使用层级技能（父→子）减少扁平数量；定期审计 skill 使用率，淘汰冷门 skill |
| ⑤ | **纯文档驱动，无输出拦截**：Agent 读取 SKILL.md 后可自由改写、总结或重新格式化输出，无后处理/输出拦截机制 | 🟢 低 | ⚠️ 设计约束 | 对输出格式有严格要求时，配合 `structured output`（`response_format`）使用；关键判断逻辑放 tool 函数中而非 skill 指令中 |

> **来源**: [deepagentsjs #143](https://github.com/langchain-ai/deepagentsjs/issues/143) / [deepagents #923](https://github.com/langchain-ai/deepagents/issues/923) / [Evaluating Skills Blog](https://www.langchain.com/blog/evaluating-skills) / [Forum: tool isolation](https://forum.langchain.com/t/tool-isolation-between-skills/3496)

### 9.5 跨框架对比：Skills vs MCP vs GPT Actions

三者**非竞争关系**，在 AI Agent 能力栈中占据互补层级：

| 维度 | Skills (SKILL.md) | MCP (Model Context Protocol) | GPT Actions |
|------|-------------------|------------------------------|-------------|
| **层级** | 应用层 / 知识层 | 传输层 / 协议层 | 工具层 / 发布层 |
| **本质** | "教 AI 怎么做" | "给 AI 连接数据和工具" | "让 AI 调用外部 API" |
| **格式** | Markdown 指令 + 可选脚本 | JSON-RPC 工具描述 | OpenAPI / Function Schema |
| **Token 效率** | ⭐⭐⭐ 最优（元数据 ~100 tokens，渐进按需加载） | ⭐ MCP 工具列表可能消耗数万 tokens | ⭐⭐ 中等（每次请求传递 function schema） |
| **生态** | agentskills.io v0.9（30+ 平台） | OpenAI/Microsoft/Google 均支持 | ChatGPT Apps 内置 |

**实际生产中三者常组合使用**：MCP 提供工具连接基础设施，Skills 提供领域知识和最佳实践指导，GPT Actions 处理面向用户的 API 发布。

> **来源**: [Auth0: MCP vs Skills](https://auth0.com/blog/what-ai-tools-mcp-servers-and-skills-actually-do/) / [Jannik Reinhard: AI Tooling Surface 2026](https://jannikreinhard.com/2026/05/15/skills-mcp-cli-computer-use-mapping-the-ai-tooling-surface-in-2026/) / Simon Willison: "Skills 可能比 MCP 更重要——更贴近 LLM 本质（用文本引导模型），Token 效率极高"

### 9.6 可靠性数据

| 指标 | 数据 | 来源 |
|------|------|------|
| Claude Code + Sonnet 4.6 LangChain 任务通过率（无 skill） | 25% | [LangChain Skills Blog](https://www.langchain.com/blog/langchain-skills) |
| Claude Code + Sonnet 4.6 LangChain 任务通过率（有 skill） | 95%（3.8x） | 同上 |
| LangSmith 任务通过率（无 skill） | 17% | 同上 |
| LangSmith 任务通过率（有 skill） | 92%（5.4x） | 同上 |
| Skill 调用可靠性 | ~70%（显式提示后） | [Evaluating Skills](https://www.langchain.com/blog/evaluating-skills) |
| Skill 数量安全上限 | ≤ 12 个（精度一致） | 同上 |
| SKILL.md body 建议上限 | < 5000 tokens | [agentskills.io spec](https://agentskills.io/specification) |

---

## 十、Skills vs 其他概念

```
Skills   = 领域知识 + 工作流指令（"怎么做"）
Tools    = 外部能力 + API 调用（"做什么"）
Memory   = 用户状态 + 偏好（"关于谁"）
System Prompt = Agent 人格 + 通用规则（"你是谁"）
```

**选择指南**：

| 场景 | 用 |
|------|-----|
| 大量领域知识，不想占 system prompt | **Skills** |
| 需要调用外部 API / 执行计算 | **Tools** |
| 记住用户偏好跨会话 | **Memory** |
| 多个领域、不同团队维护 | **Skills**（渐进披露 + 独立文件） |
| Agent 需要可复用的 Python 函数 | **Interpreter Skills** |
| 需要安装依赖 / 跑 CLI / Shell | **Skills + Sandbox** |

---

## 十一、快速速查

```
┌──────────────────────────────────────────────────────────┐
│                   Skills 选型决策                         │
├──────────────────────────────────────────────────────────┤
│  你有现成的 DeepAgents 环境？                              │
│    ├─ 是 → create_deep_agent(skills=[...])，开箱即用      │
│    └─ 否 → 用 LangChain Middleware + @tool 自己搭         │
│                                                          │
│  Skill 需要包含可执行代码？                                 │
│    ├─ 是 → DeepAgents Interpreter Skills (module:)       │
│    └─ 否 → 纯 Markdown SKILL.md 就够了                    │
│                                                          │
│  Skill 需要安装 npm/pip 包或跑 shell？                     │
│    ├─ 是 → DeepAgents + Sandbox Backend                  │
│    └─ 否 → 纯文件级 Skills 即可                           │
│                                                          │
│  多个团队各自维护领域知识？                                  │
│    └─ Skills 最合适 — 独立文件，source precedence 分层     │
└──────────────────────────────────────────────────────────┘
```

---

## 参考资料

> 专题报告引用规范见 [`topics/INDEX.md`](INDEX.md#扩展规则)。

### 本地源文件

| 本地路径 | 官方 URL |
|----------|----------|
| `docs/official/langchain/langchain-multi-agent-skills.md` | [Skills pattern](https://docs.langchain.com/oss/python/langchain/multi-agent/skills) |
| `docs/official/langchain/langchain-multi-agent-skills-sql-assistant.md` | [Skills: SQL assistant](https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant) |
| `docs/official/deepagents/deepagents-skills.md` | [DeepAgents Skills](https://docs.langchain.com/oss/python/deepagents/skills) |
| `docs/official/deepagents/deepagents-code-memory-and-skills.md` | [Code: Memory & Skills](https://docs.langchain.com/oss/python/deepagents/code/memory-and-skills) |
| `docs/official/deepagents/deepagents-overview.md` | [DeepAgents Overview](https://docs.langchain.com/oss/python/deepagents/overview) |
| `docs/official/langchain/langchain-agents.md` | [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents) |
| `docs/official/langchain/langchain-context-engineering.md` | [Context Engineering](https://docs.langchain.com/oss/python/langchain/context-engineering) |
| `skills/deepagents-v1/references/skills-guide.md` | (本项目 skill 内置参考) |

### 外部参考

| URL | 说明 |
|-----|------|
| [Agent Skills Specification](https://agentskills.io/specification) | Agent Skills 标准规范 |
| [LangChain Skills Repository](https://github.com/langchain-ai/langchain-skills) | 官方预置 Skills 库 |

> **整理日期**: 2026-07-02
