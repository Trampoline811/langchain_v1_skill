# LangChain v1.0 Skill Suite

为**没有 LangChain v1.0（2025.11+）训练数据**的 LLM 提供 Claude Code 编码规范。
覆盖 Agent Framework / Runtime / Harness 三层 + 选型路由。

> **动机**：大多数 LLM 训练数据截止于 2025 年前，写 LangChain 代码时会用 2023 年的 v0.x API（`AgentExecutor` + `ChatOpenAI` + `create_react_agent`），运行时报错。这些 skill 强制 LLM 使用正确的 v1.0 API。

## 盲测结果

| 条件 | 得分 | 根本原因 |
|------|:--:|------|
| Skill **开启** | **10/10** | API 全对 |
| Skill **关闭** | 0/10 | LLM 使用 2023 年 v0.x API |

> 详见 [`tests/blind_test_analysis.md`](tests/blind_test_analysis.md)

## 快速开始

**你只需要 `skills/` 目录。** 把它复制到 Claude Code 的 skills 文件夹即可。

### 方式一：直接复制（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/Trampoline811/langchain_v1_skill.git
# 或 Gitee：
git clone https://gitee.com/trampoline811/langchain_v1_skill.git

# 2. 复制你需要的 skill 到 Claude Code skills 目录
#    Windows: %USERPROFILE%\.claude\skills\
#    macOS:   ~/.claude/skills/
#    Linux:   ~/.claude/skills/

cp -r langchain_v1_skill/skills/langchain-v1 ~/.claude/skills/
cp -r langchain_v1_skill/skills/agent-sdk-router ~/.claude/skills/
# ... 按需复制
```

### 方式二：只下载 skills 目录（稀疏检出）

```bash
git clone --no-checkout https://github.com/Trampoline811/langchain_v1_skill.git
cd langchain_v1_skill
git sparse-checkout init --cone
git sparse-checkout set skills
git checkout master
# 现在只有 skills/ 目录
```

### 方式三：手动下载单个文件

直接访问 [skills/](skills/) 目录，下载对应 `SKILL.md` 放到你的 skills 文件夹。

## Skill 目录

| Skill | 层级 | 用途 | 触发场景 |
|-------|------|------|---------|
| [agent-sdk-router](skills/agent-sdk-router/SKILL.md) | 入口 | 官方 4+1 选型决策表 → 跳转子 skill | "构建智能体""选哪个库" |
| [langchain-v1](skills/langchain-v1/SKILL.md) | Framework | `create_agent` / `@tool` / `middleware` / `checkpointer` | 写 LangChain agent 代码 |
| [langgraph-v1](skills/langgraph-v1/SKILL.md) | Runtime | `StateGraph` / Functional API / persistence / HITL / subgraphs | 图编排 / 持久化 / 中断 |
| [deepagents-v1](skills/deepagents-v1/SKILL.md) | Harness | 文件系统 / 子Agent / 规划 / 上下文管理 | 复杂多步自主任务 |
| [langsmith-trace](skills/langsmith-trace/SKILL.md) | 观测 | CLI trace 查询 / 5 步排障 / IO 检查 | Debug Agent / 加 Tracing |

## 三层架构

> 术语来源：Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

```
agent-sdk-router   ← 入口：Framework / Runtime / Harness / Observability？
    │
    ├── langchain-v1   ← Agent Framework
    │                     create_agent, @tool, middleware, checkpointer
    │                     底层 agent loop 跑在 LangGraph runtime 之上
    │
    ├── langgraph-v1   ← Agent Runtime
    │                     StateGraph, Functional API, persistence, HITL, subgraphs
    │                     "both a runtime and a framework" — Harrison Chase
    │
    ├── deepagents-v1  ← Agent Harness（预组装电池包）
    │                     规划 + 文件系统 + 子Agent + 记忆 全部内置
    │
    └── langsmith-trace ← Observability（跨层观测）
                          CLI trace 查询 / 5 步排障 / Trace 树解读
```

## 选型速查

| 你想… | 用 |
|--------|-----|
| 快速开始，团队标准化 | **LangChain** `create_agent()` |
| 底层控制图拓扑，长运行有状态 | **LangGraph** `StateGraph` |
| 自主型 Agent，开箱即用 | **DeepAgents** `create_deep_agent()` |
| Debug Agent 行为 / 加观测 | **LangSmith Trace** `langsmith trace list` |
| 不知道该用哪个 | `/agent-sdk-router` |

## 竞品对标

| 层级 | LangChain 系 | 其他 |
|------|-------------|------|
| Framework | LangChain | AI SDK, LlamaIndex, CrewAI, Google ADK, OpenAI Agents SDK |
| Runtime | LangGraph | Temporal, Inngest |
| Harness | DeepAgents | Claude Agent SDK |

## 仓库结构

```
langchain_v1_skill/
├── skills/          ★ 你需要的 — 5 个 Claude Code Skill
├── tests/           盲测验证（可信度背书）
├── results/         盲测结果归档
├── tools/           维护工具（自己同步官方文档用，见下方说明）
└── README.md
```

> `docs/` 不在仓库中（`.gitignore` 排除）。skill 的构建素材来自 LangChain 官方文档，最终用户不需要。

## 自行维护

如果你想**自己维护这些 skill**，跟踪 LangChain 官方文档更新并同步到 skill：

```bash
# 1. 同步官方文档到本地
python tools/update_skill.py --docs-only

# 2. 检查哪些关键文件变了
#    输出会告诉你 langchain-agents、langchain-tools 等是否更新

# 3. 手动修改对应 SKILL.md（只改变化的部分）

# 4. 跑功能验证
python tools/update_skill.py --test-only

# 5. 打包归档
python tools/update_skill.py --package
```

`tools/urls.md` 维护了 ~110 条官方文档源 URL，脚本逐条拉取 GitHub raw `.mdx` 并清洗为纯净 Markdown。完整维护流程见 [`tests/maintenance_guide.md`](tests/maintenance_guide.md)。

## 更新日志

| Skill | 最近更新 |
|-------|------|
| agent-sdk-router | 2026-06-22 新增 LangSmith Trace 路由 + 5 步排障场景 |
| langchain-v1 | 2026-06-22 新增 3 个 reference（国产模型/踩坑/Trace）+ 洋葱模型 + 流式增强 |
| langgraph-v1 | 2026-06-14 更新 Runtime 定位 + 设计模式 §11 |
| deepagents-v1 | 2026-06-14 新增 Harness 定位 + 中间件装配 + 异步子Agent |
| langsmith-trace | 2026-06-22 新建 — CLI 安装 / 5 步排障 / Trace 树解读 |

各 skill 独立 `CHANGELOG.md` 见对应目录。

## 协议

MIT
