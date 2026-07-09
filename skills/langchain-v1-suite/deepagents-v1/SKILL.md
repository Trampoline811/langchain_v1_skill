---
name: deepagents-v1
description: Deep Agents 开箱即用 agent harness 代码生成规范。内置文件系统、子agent、规划、上下文管理、代码执行。当用户需要复杂多步任务、代码生成/执行、深度研究、内容构建等完整 agent 堆栈时使用。触发词：deepagents、create_deep_agent、sandbox、代码执行、filesystem、文件系统、长任务、subagent 集群、深度研究、内容构建、FilesystemMiddleware、SubAgentMiddleware、SkillsMiddleware、MemoryMiddleware。
---

# Deep Agents v1 编码规范

> Deep Agents = `create_agent()` + **预组装中间件堆栈**。内置文件系统、摘要、子 agent、记忆、技能。
> `create_deep_agent()` 开箱即用；需要精细控制时用 `create_agent()` + 手选中间件。

## 定位：Agent Harness

> LangChain 官方定义：DeepAgents 是 **Agent Harness**（代理即用电池包）——比 Framework 更高层，"a general purpose version of Claude Code"。
> LangChain 是 Agent Framework（抽象层），LangGraph 是 Agent Runtime（基础设施层），DeepAgents 是 Agent Harness（预组装层）。
> — Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)
> 💡 不确定用哪个？→ 回到父技能 `skills/langchain-v1-suite/SKILL.md` 查路由决策表

## ⚠️ 选型边界：什么时候**不该**用 Deep Agents

> 菜刀功能齐全，但修指甲该用指甲刀。Deep Agents 不是万能答案。

### ✅ 该用 Deep Agents 的信号

- 任务涉及**多文件读写**、多步骤规划、子任务委派
- 需要**自动上下文管理**（大结果卸载、对话压缩）
- 需要**跨会话持久化记忆**（用户偏好、累积知识）
- 需要**子 Agent 并行或异步执行**
- 任务复杂到"Agent 一次 invoke 不够用"

### ❌ 不该用 Deep Agents 的信号 — 用 `create_agent()` 就够了

- **单轮问答**、简单 tool-calling（查天气、算数学、翻译）
- **不需要文件系统**、不涉及多步骤规划
- 上下文短、一次调用就能完成
- 用户明确说"简单"、"快速"、"轻量"
- 只需要 1-2 个工具，且工具返回很短

### 🔀 该直接用 LangGraph 的信号 — 跳过 Deep Agents

- 需要**精细控制图编排**（分支、循环、条件边）
- 需要自行管理 checkpoint 和 state schema
- Deep Agents 的预设中间件反而碍事
- 已有成熟的 LangGraph 图，只想加 Agent 能力 → 用 `create_agent()` + 自定义中间件

### 竞品对比速查

| 维度 | Deep Agents | Claude Agent SDK | Codex SDK |
|------|-------------|------------------|-----------|
| 模型绑定 | **模型无关** 100+ | 绑定 Claude | 绑定 OpenAI |
| 长期记忆 | ✅ StoreBackend | ❌ | ❌ |
| 虚拟文件系统 | ✅ 可插拔后端 | 本地 | 本地 |
| 沙箱执行 | ✅ Sandbox-as-Tool | ❌ | ✅ OS 级 |
| 生产部署 | LangSmith 全链路 | 自定义 HTTP | 云端 |

> **一句话**：需要模型灵活性 + 跨会话记忆 → Deep Agents。全员 Claude → Claude Agent SDK。全员 OpenAI → Codex SDK。

## 定位

```
DeepAgents  ← 预组装 harness ← 你现在在这
    │         内置: FilesystemMiddleware + SummarizationMiddleware
    │         + SubAgentMiddleware + MemoryMiddleware + SkillsMiddleware
    │         适用: 长任务、代码生成、深度研究、内容构建
    │
LangChain   ← Agent框架 (create_agent, @tool, middleware)
    │
LangGraph   ← 编排运行时 (StateGraph, persistence, streaming)
```

---

## 1. 快速开始

```python
# pip install deepagents langchain-openai
from deepagents import create_deep_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="You are a helpful assistant.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in SF?"}]}
)
```

### 国内模型配置（硅基流动直连）

无需代理，兼容 OpenAI 接口，永久免费模型可用：

```python
from langchain_openai import ChatOpenAI
import os

# 免费模型（学习实验）
model = ChatOpenAI(
    model="THUDM/glm-4-9b-chat",  # 128K 上下文，支持 Tools，永久免费
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

# 推荐模型（实际项目）
# "Pro/zai-org/GLM-5"        — 智谱旗舰，Agent 任务最佳
# "Pro/moonshotai/Kimi-K2.5" — Kimi 旗舰，256K 上下文
# "Qwen/Qwen3.5-27B"         — Qwen 最新，支持思考模式
# "deepseek-ai/DeepSeek-V3.2"— 推理 + Agent 顶级
```

> `ChatOpenAI` + `base_url` 是接入国内平台的通用模式——换 URL 和 Key 就能切 DeepSeek、智谱、阿里云等。

**`create_deep_agent()` 自动装配：**
- `FilesystemMiddleware` — 虚拟文件系统，读写文件跨轮次保留
- `SummarizationMiddleware` — 上下文超限自动压缩
- `SubAgentMiddleware` — 内置 `general-purpose` 子 agent
- `MemoryMiddleware` — 从 `AGENTS.md` 加载持久记忆
- `SkillsMiddleware` — 从 `skills/` 目录加载领域知识

---

## 2. 内置能力

### 2.1 文件系统（FilesystemMiddleware）

```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    backend=StateBackend(),  # 或 FilesystemBackend(root_dir="...")
)

# Agent 自动获得文件系统工具：read_file, write_file, edit_file, ls, glob, grep
# 文件跨轮次持久化在 state 中
```

**六种 Backend 完整参考：**

| Backend | 存储位置 | 持久化 | 适用场景 | 安全风险 |
|---------|---------|:--:|------|------|
| `StateBackend()` | Agent state（内存） | 同线程内 | 默认选择、临时草稿纸 | 低 |
| `FilesystemBackend(root_dir)` | 本地磁盘 | ✅ 永久 | 本地 CLI、编程助手 | ⚠️ 可读 `.env` 等敏感文件 |
| `LocalShellBackend(root_dir)` | 本地磁盘 + Shell | ✅ 永久 | 个人开发机 | 🔴 可执行任意命令 |
| `StoreBackend(namespace=...)` | LangGraph Store | ✅ 跨会话 | 长期记忆、知识库 | 低 |
| `CompositeBackend(routes={...})` | 混合路由 | 混合 | 多后端组合 | 取决于子后端 |
| 沙箱后端 | 隔离容器 | ✅ 永久 | 安全代码执行 | 低 |

**CompositeBackend 混合路由：**不同路径自动走不同后端：

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),           # 默认临时
        routes={
            "/memories/": StoreBackend(    # /memories/ 下持久化
                namespace=lambda rt: (rt.server_info.user.identity,),
            ),
        },
    ),
)
# Agent 写入 /workspace/plan.md → StateBackend（临时）
# Agent 写入 /memories/prefs.txt → StoreBackend（跨会话持久化）
# ls/glob/grep 自动聚合所有后端结果
```

**声明式权限：**

```python
from deepagents import FilesystemPermission

# 禁止写入 /policies/ 下任何文件
FilesystemPermission(operations=["write"], paths=["/policies/**"], mode="deny")
```

**自定义后端：**实现 `BackendProtocol` 6 个方法（`ls`、`read`、`write`、`edit`、`grep`、`glob`），可接入 S3/Postgres 等任意存储。

```python
from deepagents.backends.protocol import (
    BackendProtocol, WriteResult, EditResult, LsResult,
    ReadResult, GrepResult, GlobResult,
)

class S3Backend(BackendProtocol):
    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

    def ls(self, path: str) -> LsResult:
        ...  # 列出对象，返回 FileInfo 列表

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        ...  # 返回 ReadResult(file_data=...) 或 ReadResult(error=...)

    def write(self, file_path: str, content: str) -> WriteResult:
        ...  # 外部存储后端 files_update=None

    def edit(self, file_path: str, old: str, new: str, replace_all: bool = False) -> EditResult:
        ...  # 读取 → 替换 → 写回

    def grep(self, pattern: str, path: str = None, glob: str = None) -> GrepResult:
        ...  # 正则搜索

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        ...  # 通配符匹配
```

**安全策略（PolicyWrapper / GuardedBackend）：**

对需要拦截策略（速率限制、审计日志、内容检查）的场景，继承现有后端覆写方法：

```python
class GuardedBackend(FilesystemBackend):
    def __init__(self, *, deny_prefixes: list[str], **kwargs):
        super().__init__(**kwargs)
        self.deny_prefixes = [p.rstrip("/") + "/" for p in deny_prefixes]

    def write(self, file_path: str, content: str) -> WriteResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return WriteResult(error=f"写入被拒绝：{file_path}")
        return super().write(file_path, content)

    def edit(self, file_path: str, old: str, new: str, replace_all: bool = False) -> EditResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return EditResult(error=f"编辑被拒绝：{file_path}")
        return super().edit(file_path, old, new, replace_all)
```

**后端选择指南：**

| 场景 | 推荐后端 | 理由 |
|------|---------|------|
| 学习和实验 | `StateBackend()`（默认） | 零配置，自动清理 |
| 本地编程助手 | `FilesystemBackend(root_dir=".")` | 直接操作项目文件 |
| 需要跨会话记忆 | `CompositeBackend` | 混合临时 + 持久化 |
| 需要执行代码 | 沙箱后端 | 安全隔离 |
| 生产部署 | `StoreBackend` 或 `CompositeBackend` | 持久化 + 可伸缩 |

**自动上下文管理（无感知）：**
- 工具结果 >20K tokens → 自动卸载到文件系统，对话中替换为文件引用 + 前 10 行预览
- 上下文达窗口 85% → 自动生成结构化摘要，完整记录保存到文件系统
- Agent 随时 `read_file`/`grep` 回溯完整内容

### 2.2 代码执行（Interpreters + Sandboxes）

```python
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    middleware=[
        FilesystemMiddleware(backend=StateBackend()),
        # 内置 Python 解释器 — agent 可以执行代码
    ],
)
# Agent 拥有 execute_python 工具，可运行任意代码
```

**Sandboxes 隔离级别：**
- 本地进程（默认）— 最快，无额外依赖
- Docker sandbox — 完全隔离，需 Docker
- 远程 sandbox — 通过 `remote-sandboxes` 配置

### 2.3 子 Agent（SubAgentMiddleware）

> 核心动机：**Context Quarantine（上下文隔离）**— 子 Agent 在独立上下文中工作，只返回精炼结果给主 Agent。

**字段完整参考（10 个字段 + 继承规则）：**

| 字段 | 必填 | 继承主Agent？ | 说明 |
|------|:--:|:--:|------|
| `name` | ✅ | — | 唯一标识，主 Agent 靠它指定委派给谁 |
| `description` | ✅ | — | 能力描述，主 Agent **据此决策路由**（越具体越准） |
| `system_prompt` | ✅ | ❌ 不继承 | 子 Agent 专属指令，需独立定义 |
| `tools` | 可选 | ✅ 默认继承 | 指定后**完全替换**（不合并） |
| `model` | 可选 | ✅ 默认继承 | 可指定不同模型或 `"provider:model"` 字符串 |
| `middleware` | 可选 | ❌ 不继承 | 子 Agent 自己的中间件 |
| `interrupt_on` | 可选 | ✅ 默认继承 | 可覆盖主 Agent 的 HITL 配置 |
| `skills` | 可选 | ❌ 不继承 | 指定后独立运行 SkillsMiddleware |
| `response_format` | 可选 | ❌ 不继承 | Pydantic schema 结构化输出（需 >=0.5.3） |
| `permissions` | 可选 | ✅ 默认继承 | 指定后**完全替换**（不合并） |

> 关键：`system_prompt` 和 `tools` 的继承行为不同 — tools 默认继承主 Agent，system_prompt 需要独立写。

**三种定义形态：**

| 形态 | 用法 | 适用 |
|------|------|------|
| Dict 定义 | `{"name": "...", "tools": [...], ...}` | **大多数情况**，简单直观 |
| `CompiledSubAgent` | `CompiledSubAgent(name="...", runnable=graph)` | 复用现成 LangGraph 图 |
| 转子 Agent | `create_deep_agent(name="...", ...).as_subagent()` | 快速原型 |

**General-purpose 子 Agent**（默认可用，继承主 Agent 全部能力）：

```python
# 禁用（不想让 Agent 有 task 工具时）
from deepagents.profiles import GeneralPurposeSubagentProfile, HarnessProfile
agent = create_deep_agent(
    model=model, subagents=[],
    profile=HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)),
)

# 覆盖（给默认子 Agent 配更强模型）
agent = create_deep_agent(model=model, subagents=[
    {"name": "general-purpose", "description": "通用助手", "system_prompt": "...",
     "model": ChatOpenAI(model="Pro/zai-org/GLM-5", ...)},
])
```

**结构化输出**（子 Agent → 主 Agent 返回 JSON）：`"response_format": ResearchFindings` → ToolMessage 收到 `'{"summary": "...", "confidence": 0.87}'`

**最佳实践 5 条：**
1. **描述要具体** — ✅ `"需要多次搜索、交叉验证和综合分析时使用"` vs ❌ `"做研究"`
2. **提示词要详细** — 必须含输出格式 + 字数限制，否则子 Agent 返回大量原始数据 → 上下文隔离失效
3. **工具集要精简** — 最小权限原则，只给需要的工具
4. **模型分级** — 轻量任务用免费模型，深度分析用旗舰模型
5. **输出要精练** — 强制 `"返回结果控制在 500 字以内"`

**排障 3 问：**
- 子 Agent 没被调用 → `description` 太模糊，或主 Agent system_prompt 没指示委派
- 上下文依然膨胀 → 子 Agent 返回了原始数据，未做字数限制
- 调错子 Agent → 多个 `description` 过于相似，需明确区分使用场景

### 2.4 记忆（MemoryMiddleware）

> Deep Agents 将记忆作为一等公民——Agent 以文件形式读写记忆，Backend 控制存储位置。核心机制：**文件路径路由** → `/memories/` 前缀走 StoreBackend 持久化，其他路径走 StateBackend（临时）。

**两种记忆对比：**

| 维度 | 短期记忆（Checkpointer） | 长期记忆（Store） |
|------|----------------------|------------------|
| **作用域** | 同一 `thread_id` 内 | **跨 thread、跨会话** |
| **存储层** | LangGraph Checkpointer | LangGraph Store |
| **开发用** | `MemorySaver`（内存，重启丢失） | `InMemoryStore`（内存，重启丢失） |
| **生产用** | `PostgresSaver`（DB 持久化） | `PostgresStore`（DB 持久化） |
| **典型内容** | 消息历史、文件系统状态、任务清单 | 用户偏好、项目背景、累积知识 |

**基础用法：**

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model=model,
    memory=["/memories/AGENTS.md"],       # 启动时加载到 system prompt
    backend=CompositeBackend(
        default=StateBackend(),            # 临时文件
        routes={
            "/memories/": StoreBackend(    # 持久化文件（跨会话）
                namespace=lambda rt: (rt.server_info.user.identity,),
            ),
        },
    ),
)
```

Agent 的读写完全透明——`write_file("/workspace/draft.txt")` → StateBackend（临时），`write_file("/memories/prefs.md", "简洁代码")` → StoreBackend（下次对话仍可读）。

**三种作用域：**

| 作用域 | namespace 函数 | 可见性 | 典型用途 |
|--------|---------------|--------|---------|
| **Agent 级** | `(rt.server_info.assistant_id,)` | 所有用户共享 | 项目背景、技术规范 |
| **用户级** | `(rt.server_info.user.identity,)` | 仅该用户 | 偏好设置、个人笔记 |
| **组织级** | `(org_id,)` | 全体成员（通常只读） | 合规策略、公司规范 |

```python
def agent_namespace(rt):
    return (rt.server_info.assistant_id,)

def user_namespace(rt):
    return (rt.server_info.user.identity,)

def org_namespace(rt):
    return (getattr(rt.context, "org_id", "default-org"),)
```

**四种实用场景：**

| 场景 | 做法 |
|------|------|
| 用户偏好记忆 | `memory=["/memories/preferences.md"]` → Agent 首次对话记住，后续自动加载 |
| 自我改进 Agent | Agent 记录"上次这个任务踩了什么坑"到 `/memories/lessons.md`，下次避开 |
| 知识库累积 | 多次研究对话逐渐积累到 `/memories/knowledge/`，形成个人知识库 |
| 研究项目持续推进 | 同一项目跨多次对话推进，所有中间产物持久化 |

**记忆的六个维度（设计参考）：**

| 维度 | 选项 |
|------|------|
| **内容类型** | 情景记忆（过去经历）/ 程序性记忆（Skills）/ 语义记忆（事实） |
| **作用域** | 用户级 / Agent 级 / 组织级 |
| **更新策略** | 对话中实时 / 对话间后台整合 |
| **检索方式** | 启动加载（`memory=`）/ 按需读取（文件系统工具） |
| **权限控制** | 读写 / 只读（组织策略防注入） |
| **并发写入** | 多 Agent 同时写同一文件 → last-write-wins |

**生产升级路径：**

```python
# 开发阶段
from langgraph.store.memory import InMemoryStore
store = InMemoryStore()

# 生产阶段
from langgraph.store.postgres import PostgresStore
import os

with PostgresStore.from_conn_string(os.environ["DATABASE_URL"]) as store:
    store.setup()  # 首次自动建表
    agent = create_deep_agent(
        model=model,
        memory=["/memories/AGENTS.md"],
        store=store,  # ← 传入生产 Store
        backend=CompositeBackend(
            default=StateBackend(),
            routes={"/memories/": StoreBackend(namespace=user_namespace)},
        ),
    )
```

> **最佳实践**：(1) 用描述性路径如 `/memories/project/tech-stack.md` 而非 `/memo.txt`；(2) 用 `memory=` 声明而非在 system_prompt 里手写；(3) 按主题拆分文件；(4) 组织级策略设只读防注入攻击。

### 2.5 技能（SkillsMiddleware）

> Skills = 目录结构 `SKILL.md` + 可选 `scripts/` `references/` `assets/`。
> Deep agent skills 遵循 [Agent Skills 规范](https://agentskills.io/specification)。
> 核心机制：**渐进披露（Progressive Disclosure）**— Agent 只在需要时加载完整技能内容。

**基础结构：**

```python
from deepagents.middleware import SkillsMiddleware

SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],  # 技能目录，按需加载
)
```

```
skills/
├── langgraph-docs/
│   └── SKILL.md            # 必需：YAML frontmatter + markdown 指令
├── arxiv-search/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── search.py      # 可执行脚本
│   └── references/
│       └── api-guide.md    # 参考文档
└── order-helpers/
    ├── SKILL.md
    └── assets/
        └── template.json   # 模板等资源
```

**Interpreter Skills（可执行代码技能）：**

```python
# skills/arxiv-search/SKILL.md  frontmatter:
# ---
# name: arxiv-search
# description: Search arxiv for research papers
# module: scripts/search.py     ← 关键：声明为 interpreter skill
# ---

# skills/arxiv-search/scripts/search.py
def search_arxiv(query: str, max_results: int = 10) -> dict:
    """Search arxiv API and return structured results."""
    import requests
    resp = requests.get(f"https://api.arxiv.org/...")
    return resp.json()
```

> Interpreter skills 的 `module` frontmatter 让 Agent 可以将 skill 加载为可调用 Python 模块。

**技能权限（Skill Permissions）：**

```python
from deepagents.middleware import SkillsMiddleware

SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],
    permissions={
        # 所有用户共享技能
        "langgraph-docs": {"type": "shared", "users": "*"},
        # 限定用户才能用
        "admin-tools": {"type": "limited", "users": ["admin", "operator"]},
        # 只读（禁止 Agent 写入修改）
        "compliance-rules": {"type": "read_only"},
        # Agent 可编辑的个人技能
        "my-notes": {"type": "editable", "scope": "user"},
    },
)
```

**运行时动态加载技能：**

```python
# 固定列表
agent = create_deep_agent(model=model, skills=["./skills/basic/"])

# 动态列表（按环境/用户切换）
def get_skills(runtime):
    if runtime.context.get("tier") == "pro":
        return ["./skills/basic/", "./skills/pro/"]
    return ["./skills/basic/"]

agent = create_deep_agent(model=model, skills=get_skills)

# 命名空间技能（不同用户看不同技能）
agent = create_deep_agent(model=model, skills=[
    "./skills/shared/",
    {"namespace": "user-123", "source": "./skills/personal/"},
])
```

**子 Agent 专属技能：**

```python
subagents = [{
    "name": "researcher",
    "description": "深度调研",
    "system_prompt": "你是研究员...",
    "skills": ["./skills/research/"],  # 只给 researcher 的专属技能
}]
agent = create_deep_agent(model=model, subagents=subagents)
```

**Sandbox 脚本技能** — 在隔离环境中执行 skill 代码：

```python
SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],
    sandbox=True,  # 启用沙箱执行
)
```

> 完整参考: `docs/official/deepagents-skills.md` (1012行) | [Agent Skills 规范](https://agentskills.io/specification)

---

### 2.6 中间件装配架构

> `create_deep_agent()` 的本质 = `create_agent()` + 三层自动装配的中间件堆栈。

**常驻层（5 个，始终启用，不可排除）：**

| 中间件 | 注入能力 |
|--------|---------|
| `TodoListMiddleware` | `write_todos` 工具 + 规划提示词 |
| `FilesystemMiddleware` | 6 个文件工具 + 权限控制 |
| `SummarizationMiddleware` | 对话历史自动压缩（触发阈值可配） |
| `PatchToolCallsMiddleware` | 工具调用内部修补（框架内部） |
| `AnthropicPromptCachingMiddleware` | 提示词缓存（非 Anthropic 模型自动跳过） |

**条件层（5 个，按参数自动激活）：**

| 触发条件 | 中间件 | 注入能力 |
|---------|--------|---------|
| 有子 Agent | `SubAgentMiddleware` | `task` 工具 + 子 Agent 上下文隔离 |
| 传 `skills=` | `SkillsMiddleware` | 从 `skills/` 目录加载领域知识 |
| 有异步子 Agent | `AsyncSubAgentMiddleware` | 5 把遥控器工具 |
| 传 `memory=` | `MemoryMiddleware` | 从 `AGENTS.md` 加载持久记忆 |
| 传 `interrupt_on=` | `HumanInTheLoopMiddleware` | 拦截指定工具等待人工审批 |

**用户自定义层（`middleware=[]` 按需叠加，LangChain 预构建的全部可用）：**

| 类别 | 中间件 | 用途 |
|------|--------|------|
| 安全 | `PIIMiddleware` | 个人信息检测脱敏 |
| 弹性 | `ToolRetryMiddleware` | 工具失败自动重试 |
| | `ModelRetryMiddleware` | 模型失败自动重试 |
| | `ModelFallbackMiddleware` | 主模型失败切换备用 |
| 限制 | `ToolCallLimitMiddleware` | 限制工具调用次数 |
| | `ModelCallLimitMiddleware` | 限制模型调用次数 |
| 上下文 | `ContextEditingMiddleware` | 清理旧工具调用结果 |

**手动组合对照：**

```python
# create_deep_agent() 帮你做的：
agent = create_deep_agent(model=model, tools=[search])

# 等价于 create_agent() + 手动装配：
from langchain.agents import create_agent
from langchain.agents.middleware import (
    TodoListMiddleware, FilesystemMiddleware, SummarizationMiddleware
)
agent = create_agent(
    model=model, tools=[search],
    middleware=[
        TodoListMiddleware(),
        FilesystemMiddleware(),
        SummarizationMiddleware(model=model, trigger=("tokens", 4000), keep=("messages", 20)),
    ],
)
```

**TodoListMiddleware 自定义配置：**

```python
from langchain.agents.middleware import TodoListMiddleware

TodoListMiddleware(
    system_prompt="将任务拆解为可执行的步骤，先写测试再写代码。",
    tool_description="管理任务列表的工具。每个任务包含 content（内容）和 status（状态）。",
)
```

**write_todos 任务数据结构：**

```python
# 每个任务：{"content": "任务描述", "status": "pending|in_progress|completed"}
# 状态流转：pending → in_progress → completed
```

Agent 典型行为：收到复杂任务 → 调用 `write_todos([{...pending...}, ...])` 制定计划 → 逐个执行 `pending→in_progress→completed` → 执行中发现新步骤动态追加。

**SummarizationMiddleware 触发机制：**
- `trigger=("tokens", 4000)` — 上下文超过 4000 tokens 触发压缩
- `keep=("messages", 20)` — 保留最近 20 条消息不压缩
- 压缩时会用 LLM 生成结构化摘要（意图、产出物、下一步），完整原始对话保存到文件系统
- **与 TodoListMiddleware 协同**：即使对话被压缩，任务清单仍然完整——Agent 知道当前进度

## 3. 上下文工程（Context Engineering）

Deep Agents 的核心优势：**自动管理上下文窗口**。

```python
from deepagents.backends import StateBackend
from deepagents.middleware import (
    FilesystemMiddleware,
    SummarizationMiddleware,
    MemoryMiddleware,
    SkillsMiddleware,
)

backend = StateBackend()
model = "claude-sonnet-4-6"

agent = create_deep_agent(
    model=model,
    tools=[search],
    backend=backend,
    middleware=[
        FilesystemMiddleware(backend=backend),
        SummarizationMiddleware(
            model=model,                    # 摘要用同一模型
            backend=backend,
            trigger=("tokens", 100000),      # 超 100K tokens 触发压缩
            keep=("messages", 20),           # 保留最近 20 条消息
        ),
        MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
        SkillsMiddleware(backend=backend, sources=["./skills/"]),
    ],
)
```

---

## 4. 权限控制

```python
from deepagents.middleware.permissions import PermissionsMiddleware

PermissionsMiddleware(
    allowed_tools=["read_file", "search"],   # 白名单
    denied_tools=["delete_file", "execute_shell"],  # 黑名单
    allowed_paths=["/workspace/"],           # 文件系统路径限制
)
```

---

## 5. Human-in-the-Loop

> Deep Agents 内置 `HumanInTheLoopMiddleware`，通过 `interrupt_on` 参数配置哪些工具需要人工审批。Checkpointer **必须配置**（中断恢复靠它）。

**基础用法：**

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def delete_file(path: str) -> str:
    """删除指定文件。"""
    ...

checkpointer = MemorySaver()

agent = create_deep_agent(
    model=model,
    tools=[delete_file, send_email, read_file],
    interrupt_on={
        "delete_file": True,                                        # 完全中断
        "send_email": {"allowed_decisions": ["approve", "reject"]}, # 只能批/拒
        "read_file": False,                                         # 不中断
    },
    checkpointer=checkpointer,  # 必须！
)
```

**三种配置值：**

| 配置值 | 含义 |
|--------|------|
| `True` | 启用中断，允许所有 4 种决策 |
| `False` | 不中断，Agent 直接执行 |
| `{"allowed_decisions": [...]}` | 启用中断，只允许指定决策类型 |

**四种决策类型：**

| 决策 | 含义 | 适用场景 |
|------|------|---------|
| `approve` | 批准，使用 Agent 原始参数执行 | "确认删除这个文件" |
| `edit` | 修改参数后执行 | "收件人改一下再发" |
| `reject` | 跳过调用，把拒绝原因反馈给 Agent | "不要删除，取消" |
| `respond` | 不执行工具，人的回复作为工具结果 | `ask_user` 等"问用户"的工具 |

> ⚠️ `reject` vs `respond`：拒绝副作用工具（删除/发送/部署）用 `reject`，`respond` 只用于"工具本身就是问人"的场景。

**条件中断（`when` 谓词）：**

> 需要 `langchain>=1.3.3`。

```python
from langchain.agents.middleware import ToolCallRequest

def writes_outside_workspace(request: ToolCallRequest) -> bool:
    """仅写入 /workspace/ 外时中断。"""
    path = request.tool_call["args"].get("file_path", "")
    return not path.startswith("/workspace/")

agent = create_deep_agent(
    model=model,
    interrupt_on={
        "write_file": {
            "allowed_decisions": ["approve", "edit", "reject"],
            "when": writes_outside_workspace,  # ← 条件判断
        },
    },
    checkpointer=checkpointer,
)
```

**中断与恢复完整流程：**

```python
# 1. 正常调用 — Agent 遇到中断工具时暂停
config = {"configurable": {"thread_id": "session-001"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "删除 /tmp/old.txt"}]},
    config=config,
    version="v2",  # HITL 必须用 v2
)

# 2. 检查是否有待审批项
if "__interrupt__" in result:
    for action in result["__interrupt__"]:
        print(f"Agent 想调用 {action['name']}({action['arguments']})")

    # 3. 人类做决策
    decisions = [
        {"type": "approve"},           # 批准第 1 个
        {"type": "edit", "args": {...}}, # 修改第 2 个
        {"type": "reject", "message": "原因..."},  # 拒绝第 3 个
    ]

    # 4. 恢复执行
    result = agent.invoke(
        None,  # 不追加新消息
        Command(resume={"decisions": decisions}),
        config=config,
        version="v2",
    )
```

**关键要求：**
- ✅ 必须配置 Checkpointer
- ✅ 必须相同 `thread_id`
- ✅ 必须 `version="v2"`
- ✅ `decisions` 数量和顺序与 `action_requests` 一一对应

**批量工具调用：** 一次模型调用可能触发多个工具（4 个 `write_file`），`interrupt_on` 匹配的第一个触发中断，已通过的非中断工具仍会执行。

**子 Agent 独立 HITL：**

```python
agent = create_deep_agent(
    model=model,
    tools=[delete_file, read_file],
    interrupt_on={"delete_file": True, "read_file": False},
    subagents=[{
        "name": "file-manager",
        "description": "管理文件操作",
        "system_prompt": "你是文件管理助手。",
        "tools": [delete_file, read_file],
        "interrupt_on": {
            "delete_file": True,
            "read_file": True,  # 子 Agent 读文件也要审批！
        }
    }],
    checkpointer=checkpointer,
)
```

**按风险等级分层：**

| 级别 | 工具示例 | 策略 |
|------|---------|------|
| 🟢 低风险 | `read_file`, `grep`, `search` | `False` — 不中断 |
| 🟡 中风险 | `write_file`, `edit_file` | 条件中断（`when` 谓词） |
| 🔴 高风险 | `delete_file`, `send_email`, `execute_shell` | `True` — 始终中断 |
| ⚫ 财务/合规 | `transfer_funds`, `deploy` | `{"allowed_decisions": ["approve", "reject"]}` — 不允许 edit |

---

## 6. 异步子 Agent（deepagents>=0.5.0 preview）

> ⚠️ Preview 特性，API 可能变化。同步子 Agent 阻塞主 Agent；异步子 Agent 立即返回任务 ID，主 Agent 全程不阻塞。

**同步 vs 异步：**

| 维度 | 同步 | 异步 |
|------|------|------|
| 执行模型 | 阻塞等完成 | 立即返回 task ID |
| 并发性 | 可并行，但主 Agent 被整批阻塞 | 完全并行，主 Agent 自由 |
| 中途追加指令 | ❌ | ✅ `update_async_task` |
| 取消 | ❌ | ✅ `cancel_async_task` |
| 状态性 | 每次调用独立 | 子 Agent 拥有自己的 thread，历史累积 |
| 典型场景 | 秒级快速委派 | 分钟级以上长程任务 |

**判定方法**：子任务 <5 秒 → 同步；子任务可能跑数分钟且过程需交互 → 异步。

**声明：**

```python
from deepagents import AsyncSubAgent, create_deep_agent

async_subagents = [
    AsyncSubAgent(
        name="researcher",                     # 唯一标识
        description="深度调研，多次搜索+综合分析",  # 路由依据
        graph_id="researcher",                 # Agent Protocol 上的 graph ID
        # url="https://...langsmith.dev",      # 可选：远程 HTTP，不填走 ASGI 进程内
        # headers={...},                       # 可选：自托管鉴权
    ),
]
agent = create_deep_agent(model=model, subagents=async_subagents)
```

**5 把遥控器**（`AsyncSubAgentMiddleware` 自动注入）：

| 工具 | 作用 | 返回 |
|------|------|------|
| `start_async_task` | 启动后台任务 | task ID（立即返回） |
| `check_async_task` | 查询状态与结果 | status + result（若完成） |
| `update_async_task` | 运行中追加新指令 | 确认 + 更新后状态 |
| `cancel_async_task` | 终止运行中任务 | 取消确认 |
| `list_async_tasks` | 列出所有任务及状态 | 任务总览 |

**完整生命周期：**

```
用户：深入调研 LangGraph 多 Agent 架构
主 Agent → start_async_task("researcher", "调研...") → task_id: abc-123
主 Agent ← 「已派 researcher 后台开干，你可以继续问别的」

用户：先帮我把这段代码格式化一下
主 Agent ← （直接处理，researcher 仍在后台跑）

用户：那个调研有进展吗？
主 Agent → check_async_task("abc-123") ← status: running
主 Agent ← 「还在跑，已搜了 4 个关键词，预计还要几分钟」

用户：补一下：重点关注 supervisor/network/hierarchical 三种拓扑
主 Agent → update_async_task("abc-123", "重点关注三种拓扑...") ← 已注入

用户：算了，先停一下
主 Agent → cancel_async_task("abc-123") ← cancelled
```

**设计要点：** 任务元数据存在独立的 `async_tasks` channel 中，与消息历史解耦——即使对话被压缩，主 Agent 永远能通过 `list_async_tasks` 找回所有任务。

**传输模式：**

| 模式 | 默认 | 适用 |
|------|:--:|------|
| ASGI（进程内） | ✅ | 同部署、零延迟、起手式 |
| HTTP（远程） | 传 `url` 后 | 子 Agent 需独立扩缩容/独立团队维护 |

**3 种部署拓扑：** 单部署（全 ASGI，默认）→ 拆分部署（全 HTTP）→ 混合（部分 ASGI + 部分 HTTP）

**最佳实践：**
1. 本地开发 `langgraph dev --n-jobs-per-worker 10`（每子 Agent 占 1 slot）
2. `description` 要行为导向，主 Agent 靠它路由
3. 用 thread ID 串联主 Agent trace ↔ 子 Agent trace（LangSmith 追踪）
4. system_prompt 中加：`"派出异步子Agent后必须立刻交还控制权给用户，不要主动 check"`

**排障 4 问：**
- 刚启动就立刻轮询 → system_prompt 强化"不要主动 check"
- 报告过时状态 → 先 `check_async_task` 再回答
- 任务 ID 被截断 → 换更听话的模型或 system_prompt 强调完整 ID
- 启动后长时间无返回 → worker pool 满了，调大 `--n-jobs-per-worker`

---

## 7. 生产部署

```python
# 1. 用 FilesystemBackend 替代 StateBackend
from deepagents.backends import FilesystemBackend
backend = FilesystemBackend(root_dir="./agent_workspace")

# 2. 用 PostgresSaver + PostgresStore 持久化
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

# 3. 部署到 LangSmith
# LangSmith 自动配置 checkpointer + store

# 4. 配置 profiles（模型能力精细化控制）
from deepagents.profiles import CodeAgentProfile
agent = create_deep_agent(
    model="claude-sonnet-4-6",
    profile=CodeAgentProfile(),  # 预设代码场景最佳参数
)
```

---

## 8. create_deep_agent() vs create_agent() 速查

> 完整选型决策见文首 [⚠️ 选型边界](#-选型边界什么时候不该用-deep-agents)。

| 场景 | create_agent() | create_deep_agent() |
|------|:--:|:--:|
| 简单 tool-calling | ✅ | ❌ 过重 |
| 需要写文件/跨轮次状态 | ❌ | ✅ |
| 需要自动上下文压缩 | ❌ | ✅ |
| 需要子 agent 并行/异步 | ❌ | ✅ |
| 需要代码执行沙箱 | ❌ | ✅ |
| 需要权限控制 | ❌ | ✅ |
| 需要最小依赖 | ✅ | ❌ |

---

## 9. 执行协议

1. **简单任务用 `create_agent()`** — 不要上来就 deepagents
2. **需要上下文管理 → `create_deep_agent()`** — 自动压缩 + 文件系统
3. **需要子 agent 并行 → 加 `SubAgentMiddleware`** — 每个子 agent 独立上下文
4. **生产环境用 FilesystemBackend** — StateBackend 不持久化
5. **微调中间件 → `create_agent()` + 手选 middleware`** — 精确控制堆栈
6. **Backend 选型 →** `references/backends-guide.md`
7. **子 Agent 详解 →** `references/subagents-guide.md`
8. **Skills 详解 →** `references/skills-guide.md`

---

## 10. 实战案例速查

> 完整案例源码见 `docs/community/cases/`。deepagents 最擅长**需要文件系统 + 代码执行 + 多步子任务**的复杂场景。

### 10.1 全自动数据分析 Agent

```
场景：上传 CSV/Excel → 自动清洗 → 探索分析 → 生成可视化报告
技术栈：create_deep_agent + FilesystemMiddleware + 代码解释器 + DeepSeek-OCR
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="deepseek:deepseek-chat",
    backend=FilesystemBackend(root_dir="workspace"),
    system_prompt="""You are a data analyst. 
    When the user uploads data, clean it, explore it, and generate a report.
    Use write_file to save plots and analysis results.""",
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "分析 sales.csv 的月度趋势并生成可视化"}]
})
# Agent 自动：读文件 → 清洗 → 统计 → 画图 → write_file 保存 → 输出报告
```

### 10.2 文档审核 Agent

```
场景：上传 PDF 合同 → 结构化提取条款 → 逐条合规检查 → 输出审核报告
技术栈：create_deep_agent + OCR 解析 + RAG 知识库 + HumanInTheLoopMiddleware
```

```python
from deepagents import create_deep_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_deep_agent(
    model="deepseek:deepseek-chat",
    tools=[ocr_parse, search_regulations],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={"final_approval": True}),
    ],
    system_prompt="""You audit documents for compliance.
    1. Parse the document with ocr_parse
    2. Extract key clauses
    3. Check each clause against regulations using search_regulations
    4. Write findings with write_file
    5. Call final_approval for human review before submitting""",
)
```

### 10.3 案例场景对照

| 你要做… | 用 | 参考案例 |
|---------|-----|---------|
| 自动数据分析/EDA/可视化 | `create_deep_agent` + 文件系统 + 代码执行 | [数据分析Agent](docs/community/cases/全自动数据分析可视化Agent系统.md) |
| 多模态 PDF/合同审核 | `create_deep_agent` + OCR + RAG + HITL | [文档审核Agent](docs/community/cases/LangChain%20v1.0%20文档审核类Agent开发实战.md) |
| 全栈 Agent + MCP | `create_agent` + `MultiServerMCPClient` + FastAPI | [mini ChatGPT](docs/community/cases/Ep.01%20从零搭建mini%20ChatGPT（上）.md) |
| OCR 多模态解析 | `create_agent` + MinerU/DeepSeek-OCR + vLLM | [OCR PDF](docs/community/cases/LangChain1.0%20+%20OCR%20多模态PDF解析实战.md) |
