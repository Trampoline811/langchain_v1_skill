# LangChain v1.0 Skill Suite — 项目维护指南

## 项目背景

2025年11月 LangChain 进入 1.0 时代，API 发生根本性变化：
- `create_agent()` 取代 `AgentExecutor` + `create_react_agent()`
- `init_chat_model()` 取代 `ChatOpenAI()`
- `@tool` 装饰器 + `ToolRuntime` 取代旧式 tool 定义
- `middleware` 体系取代 `ConversationBufferMemory`
- `checkpointer` 体系统一持久化

**核心问题**：绝大多数 LLM 训练数据截止于 2025 年前，编写 LangChain 代码时会使用旧版 v0.x API，
导致运行时报错。本项目通过 Codex Skill 机制，将 LangChain 1.0 官方文档提炼为编码规范，
强制 LLM 使用正确的 v1.0 API。

## 仓库地址

| 平台 | URL |
|------|-----|
| GitHub | https://github.com/Trampoline811/langchain_v1_skill |
| Gitee | https://gitee.com/trampoline811/langchain_v1_skill |

两个远端始终保持同步。当前分支：`master`。

## 三层架构（官方定位）

> 术语来源：Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

```
agent-sdk-router   ← 入口决策：Framework / Runtime / Harness？
    │
    ├── langchain-v1   ← Agent Framework（create_agent, @tool, middleware, checkpointer）
    │                     LangChain 1.0 的 agent loop 跑在 LangGraph runtime 之上
    │
    ├── langgraph-v1   ← Agent Runtime（StateGraph, Functional API, persistence, HITL, subgraphs）
    │                     durable execution / streaming / HITL / persistence
    │
    └── deepagents-v1  ← Agent Harness（规划 + 文件系统 + 子Agent + 记忆 全部内置）
                         create_deep_agent() — 预组装电池包
```

**决策逻辑**：
- 能用 `create_agent()` 解决的 → LangChain（90%场景）
- 需要自定义图拓扑/持久化/中断 → LangGraph
- 复杂多步自主任务 → DeepAgents
- 不确定 → `/agent-sdk-router`

## 仓库结构

```
langchain_v1/
├── README.md                     # 公开入口 — 面向最终用户的简明说明
├── AGENTS.md                     # 本文件 — 维护者专用，不推送（.gitignore）
├── skills/                       # 核心产物 — 4 个 Codex Skill
│   ├── agent-sdk-router/         # 入口路由 skill（30行）
│   │   └── SKILL.md
│   ├── langchain-v1/             # Framework skill（426行 + 5个reference）
│   │   ├── SKILL.md
│   │   ├── CHANGELOG.md
│   │   └── references/           # 详细API参考、决策指南、迁移对比等
│   │       ├── api-reference.md
│   │       ├── decision-guide.md
│   │       ├── mcp-integration.md
│   │       ├── migration-comparison.md
│   │       └── patterns.md
│   ├── langgraph-v1/             # Runtime skill（362行）
│   │   ├── SKILL.md
│   │   └── CHANGELOG.md
│   └── deepagents-v1/            # Harness skill（560行）
│       ├── SKILL.md
│       └── CHANGELOG.md
├── docs/                         # 文档素材 — skill 的源头（.gitignore 排除）
│   ├── official/                  # 官方文档下载副本（106个文件）
│   │   ├── langchain/             #   LangChain Framework（44个）
│   │   ├── langgraph/             #   LangGraph Runtime（25个）
│   │   ├── deepagents/            #   Deep Agents Harness（32个）
│   │   ├── concepts/              #   跨产品概念（4个）
│   │   └── releases-changelog.md  #   版本日志
│   └── community/                 # 🆕 社区/实战案例
│       ├── cases/                 #   完整项目示例
│       └── patterns/              #   代码模式、最佳实践
├── tools/                        # 维护工具
│   ├── update_skill.py           # 自动化同步脚本
│   └── urls.md                   # 官方文档源URL清单（~110条）
├── tests/                        # 盲测验证
│   ├── blind_test.md             # 盲测方法
│   ├── blind_test_analysis.md    # 盲测分析报告
│   ├── maintenance_guide.md      # 维护流程指南
│   └── resume_agent.py           # 功能验证用例
└── results/                      # 盲测结果归档
    └── 20250602/                 # 按日期归档
```

## 对外发布策略

**`AGENTS.md` 不推送到 GitHub/Gitee**。他人 clone 仓库后只看到：
- `README.md` — 项目说明、三层架构、安装方式、选型速查
- `skills/` — 可直接使用的 4 个 Skill
- `docs/` — 已通过 `.gitignore` 排除（素材，最终用户不需要）
- `tools/` — 仅维护者需要

`.gitignore` 已排除：`docs/`、`.venv/`、`__pycache__/`、`*.pyc`、`.docs_cache.json`、`langchain_docs/`、`AGENTS.md`

## 维护流程

### 触发条件

| 信号 | 检测方式 |
|------|---------|
| LangChain 发布新 minor 版本（1.x → 1.y） | 关注 `releases-changelog.md` 或 PyPI |
| 用户报告 skill 生成的代码过时报错 | 日志/反馈 |
| 定期巡检（建议每 2-3 月一次） | 日历提醒 |
| 收到新版官方文档或社区案例 | 手动触发 |

### 全量更新流程（~30分钟）

#### Step 1：同步官方文档

```bash
# 下载最新的官方 .mdx 文件
python tools/update_skill.py --docs-only

# 或手动：从 docs.langchain.com 拉取最新页面
# URL → GitHub raw .mdx 映射规则：
# docs.langchain.com/oss/python/X → raw.githubusercontent.com/langchain-ai/docs/main/src/oss/X.mdx
```

#### Step 2：对比差异

```bash
git diff docs/
```

重点关注：
- `create_agent` 签名是否有新参数
- `init_chat_model` 参数变化
- 新增/废弃的 middleware
- `create_deep_agent` API 变化
- `StateGraph` API 变化

#### Step 3：更新 Skill

只改相关部分，不改整体结构：

| 文件 | 更新内容 |
|------|---------|
| `SKILL.md` | 新增/废弃的 API 签名、核心速查表 |
| `references/api-reference.md` | 中间件增删、参数变化 |
| `references/migration-comparison.md` | 如有破坏性变更才更新 |
| `CHANGELOG.md` | 记录本次更新内容 |

#### Step 4：验证

```bash
python tools/update_skill.py --test-only

# 或用盲测用例
python tests/resume_agent.py --demo
# 确认无 deprecation warning，输出正常
```

### 轻量检测（只检测不下载）

```bash
curl -sL https://docs.langchain.com/llms.txt | grep -oP 'https://[^ ]+' | sort > llms_new.txt
diff llms_old.txt llms_new.txt
```

## 官方文档源 URL

全部来源：`https://docs.langchain.com/oss/python/`

### LangChain Framework（~50条）
在 `tools/urls.md` 中维护完整列表，包括：
- 核心：overview, quickstart, agents, models, tools, messages
- 中间件：middleware/overview, middleware/built-in, middleware/custom
- 前端集成：frontend/overview, frontend/integrations/*
- 多智能体：multi-agent/* (subagents, handoffs, skills, router, custom-workflow)
- 进阶：streaming, structured-output, context-engineering, RAG, guardrails
- 集成：MCP, SQL agent, voice agent, knowledge-base

### LangGraph Runtime（约5-10条）
- graph-api, agentic-rag, sql-agent
- concepts/products, concepts/providers-and-models, concepts/memory, concepts/context

### Deep Agents Harness（约3-5条）
- data-analysis, deep-research, content-builder

## 核心原则

1. **不要手动维护 API 签名** — 从 GitHub 拉最新 .mdx 是最准确的
2. **diff 驱动更新** — 只看变化部分，不重写整个 skill
3. **保留盲测用例** — `resume_agent.py` 每次更新后跑一遍
4. **版本标注** — 在 SKILL.md frontmatter 中记录基于哪个版本的文档
5. **AGENTS.md 不推送** — 维护上下文仅本地使用
6. **GitHub + Gitee 同步** — 每次 push 同时推两个远端

## 已知问题 & 待办

- [x] langgraph-v1 和 deepagents-v1 缺少 references/ 目录（langchain-v1 已有5个） ✅ 2026-06-14
- [x] docs/ 分层：official/ vs community/ ✅ 2026-06-14
- [x] README 使用说明精简 ✅ 2026-06-14
- [x] tools/update_skill.py 路径已修复 + 新增 --check 模式 ✅ 2026-06-14
- [x] Step 5a: 社区文档 → 全部 4 个 skill 已更新 ✅ 2026-06-14
- [x] Step 5b: 筛选 141 个新官方 URL → 下载 → diff → 精修 skill ✅ 2026-06-14
- [x] langgraph-v1 / deepagents-v1 盲测用例 ✅ 2026-06-15
