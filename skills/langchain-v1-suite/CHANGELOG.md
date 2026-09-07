# langchain-v1-suite CHANGELOG

## 2026-09-07 — docs 镜像收尾对账（.md 双后缀 bug 修复 + ToolErrorMiddleware 补齐）

- **langchain-v1**：§5.1 速查表 + api-reference 补 `ToolErrorMiddleware`（需 langchain>=1.3.14），官方内置中间件全集对账唯一缺口
- **langgraph-v1 / langsmith-trace / deepagents-v1**：本轮镜像收尾对账无新增 API 缺口（dynamic-subagents / fault-tolerance / rubric 内容已由 2026-09-05 同步先行覆盖）
- **来源** 官方 middleware/built-in + fault-tolerance + 全量 llms.txt 镜像（215 唯一 URL 全覆盖，docs_failed.json 清空）

## 2026-09-05 — 2026-09 全面同步（沧海九粟 ch13-16 + 官方 v0.7/v1.4）

- **deepagents-v1**：新增 v0.7 版本基线（breaking 对照 + 迁移扫描清单）、QuickJS Interpreters/PTC（§2.2 重写）、动态子 Agent（§2.8）、RubricMiddleware 评分量规（§2.9）、Streaming v3（§12）、MCPAdapter 双轨（§10）
- **langchain-v1**：MCP 章节新增 langchain>=1.4 `langchain.mcp.MCPAdapter` 分叉指引
- **来源** 沧海九粟《Deep Agents 实战》ch13-grading-rubrics / ch14-streaming / ch15-interpreters / ch16-dynamic-subagents / release-v0-7 + 官方 changelog（deepagents v0.7.0 / langchain v1.4.0）

## 2026-07-03 — 层级结构重构

### 架构变更
- **新建父技能 `langchain-v1-suite`** — 统一入口，含路由决策表 + 三层架构 + 子技能索引
- **吸收 `agent-sdk-router`** — 路由逻辑融入父技能，删除独立路由 skill
- **4 子技能归入父目录** — `langchain-v1/`, `langgraph-v1/`, `deepagents-v1/`, `langsmith-trace/` 移至 `langchain-v1-suite/` 下
- **渐进披露** — 父技能自动加载（~800 tokens），子技能按需 `read_file`

### 效果
- 自动加载 skill：5→1（-80% context 占用）
- 路由：独立 skill 中转 → 父 skill 直接路由
- 模式：matches DeepAgents Hierarchical Skills 规范 (Section 8.2)
