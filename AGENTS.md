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
langchain-v1-suite  ← 层级入口：路由决策表 + 子技能索引（吸收原 agent-sdk-router）
    ├── langchain-v1     ← Agent Framework（create_agent, @tool, middleware, checkpointer）
    ├── langgraph-v1     ← Agent Runtime（StateGraph, Functional API, persistence, HITL, subgraphs）
    ├── deepagents-v1    ← Agent Harness（规划 + 文件系统 + 子Agent + 记忆 + Rubric/Interpreter）
    └── langsmith-trace  ← Observability（跨层排障）
```

**决策逻辑**：
- 能用 `create_agent()` 解决的 → LangChain（90%场景）
- 需要自定义图拓扑/持久化/中断 → LangGraph
- 复杂多步自主任务 → DeepAgents
- 不确定 → 读父技能 `skills/langchain-v1-suite/SKILL.md` 路由决策表

## 仓库结构

```
langchain_v1/
├── README.md                     # 公开入口 — 面向最终用户的简明说明
├── AGENTS.md                     # 本文件 — 项目维护指南（已入库，随仓库推送）
├── CLAUDE.md                     # Claude Code 维护入口（.gitignore，仅本地）
├── skills/                       # 核心产物 — 唯一真相源（1 父技能 + 4 子技能）
│   └── langchain-v1-suite/
│       ├── SKILL.md              # 父技能：路由决策表 + 子技能索引 + CHANGELOG
│       ├── CHANGELOG.md
│       ├── langchain-v1/         # Framework skill（SKILL + CHANGELOG + references/* 多份）
│       ├── langgraph-v1/         # Runtime skill（SKILL + CHANGELOG + references/）
│       ├── deepagents-v1/        # Harness skill（SKILL + CHANGELOG + references/）
│       └── langsmith-trace/      # Observability skill（SKILL + CHANGELOG + reference/）
├── docs/                         # 文档素材 — skill 的源头（.gitignore 排除，不推送）
│   ├── official/                 #   官方文档镜像（.md 直出，按 langchain/langgraph/deepagents 分目录）
│   │   └── releases-changelog.md #   版本日志
│   └── community/                #   社区素材（沧海九粟/赋范 等，含 INDEX.md）
├── topics/                       # 专题研究报告（基于 docs/ 加工）
├── tools/                        # 维护工具
│   ├── update_skill.py           # 官方 .md 直出同步 + --refresh 自动合并清单 + 盲测/打包
│   └── urls.md                   # 官方 URL 清单（可由 --refresh 自动更新）
├── tests/                        # 盲测验证（resume_agent / langgraph_agent / deep_agent，17/17）
└── results/                      # 盲测结果归档（按日期）
```

## 对外发布策略

仓库推送内容（GitHub/Gitee）：
- `README.md` — 项目说明、三层架构、安装方式、选型速查
- `AGENTS.md` / `skills/`（langchain-v1-suite 整套） — 可直接使用
- `tools/` `tests/` `topics/` `.claude/` `CHANGELOG.md` — 维护上下文

`.gitignore` 已排除：`docs/`、`.venv/`、`__pycache__/`、`*.pyc`、`.docs_cache.json`、`langchain_docs/`、`.memsearch/`、`CLAUDE.md`、`docs_refresh.log`、`docs_failed.json`

> **部署副本**：`E:\AI_skill\`（套件 + 4 平铺）与 `~/.agents/skills/langchain-v1` 为 **junction 直通真相源**（2026-09-05 起），零同步、禁 cp 覆盖，详见 `.claude/maintenance/sync-strategy.md`。

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
# 下载最新的官方文档（.md 直出；默认先自动 --refresh 合并官方 llms.txt 清单）
python tools/update_skill.py --docs-only
# 仅刷新 urls.md 清单： python tools/update_skill.py --refresh

# 官方源码树已重构（src/oss/python/* → src/oss/{langchain,deepagents,langgraph}/*），
# 旧"GitHub raw .mdx"映射会 404；现统一走 docs.langchain.com/<page>.md 直出（脚本已内置重试+限速）
```

#### Step 2：对比差异

```bash
# docs/ 不入库（.gitignore），无 git diff；以脚本输出为准：
python tools/update_skill.py --docs-only   # 看 Results: X new | Y updated | W failed
# .docs_cache.json 记录每个页面的内容 hash，UPDATED 即内容有变化
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

全部来源：`https://docs.langchain.com/oss/python/`（现行分区：**langchain 79 / langgraph 43 / deepagents 40 / concepts 4**，2026-09-05 由官方 llms.txt 核对）

- 完整清单：`tools/urls.md`（由 `python tools/update_skill.py --refresh` 自动从官方分区 llms.txt 合并，**不要手工维护 URL**）
- 关键页覆盖：langchain agents/models/tools/messages/middleware{overview,built-in,custom}/mcp/multi-agent{handoffs,subagents,skills,router}/frontend、langgraph graph-api/use-graph-api/functional-api/persistence/checkpointers/stores/pregel/streaming/fault-tolerance、deepagents overview/backends/tools/subagents/skills/sandboxes/interpreters/rubric/permissions/customization/profiles/event-streaming

## 核心原则

1. **不要手动维护 API 签名** — 官方 docs 全量镜像用 `update_skill.py --docs-only`（.md 直出 + 自动刷新清单）
2. **diff 驱动更新** — 只看变化部分，不重写整个 skill
3. **保留盲测用例** — `tests/*.py` 每次更新后在 `.venv` 中跑一遍（17/17）
4. **版本标注** — 在 SKILL.md frontmatter / CHANGELOG 记录基于哪个版本
5. **部署 junction** — `E:\AI_skill\` 与 `~/.agents/skills/langchain-v1` 为 junction，改 `skills/` 即生效，禁 cp 覆盖
6. **GitHub + Gitee 同步** — 每次 push 同时推两个远端

## 已知问题 & 待办

- [x] langgraph-v1 和 deepagents-v1 缺少 references/ 目录（langchain-v1 已有5个） ✅ 2026-06-14
- [x] docs/ 分层：official/ vs community/ ✅ 2026-06-14
- [x] README 使用说明精简 ✅ 2026-06-14
- [x] tools/update_skill.py 路径已修复 + 新增 --check 模式 ✅ 2026-06-14
- [x] Step 5a: 社区文档 → 全部 4 个 skill 已更新 ✅ 2026-06-14
- [x] Step 5b: 筛选 141 个新官方 URL → 下载 → diff → 精修 skill ✅ 2026-06-14
- [x] langgraph-v1 / deepagents-v1 盲测用例 ✅ 2026-06-15
