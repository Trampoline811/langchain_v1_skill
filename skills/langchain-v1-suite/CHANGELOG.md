# langchain-v1-suite CHANGELOG

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
