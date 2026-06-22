# agent-sdk-router 更新日志

## 2026-06-22 (AgentSeek 对标 — LangSmith Trace)

- **新增** 决策表 LangSmith Trace 行：观测排障 → `/langsmith-trace`
- **新增** 场景对照：Agent 行为异常排障场景
- **更新** 执行协议：4 个跳转目标 → 5 个 + §5 先查 Trace
- **来源** AgentSeek `skills/langsmith-trace/` (ob-labs/agentseek)

## 2026-06-14 (Step 5b — 官方文档同步)

- **对齐** 官方 concepts 文件最新模型版本引用（`gpt-5.4→gpt-5.5`、`claude-opus-4-6→claude-opus-4-8`），skill 内容无实质性变更
- **来源** `concepts-providers-and-models.md` / `concepts-memory.md` 次要更新

## 2026-06-14 (第二次更新)

- **新增** 场景对照表：8 个实战场景 → 选型映射，来自社区 5 个案例 + Part 1~6 教程
- **增强** 执行协议：新增"可以在一个项目混用"指导原则
- **来源** 社区文档 `docs/community/cases/` + `docs/community/patterns/`

## 2026-06-14

- **初始创建** LangChain 官方三选一决策表（Framework / Runtime / Harness）+ 竞品对标
- **来源** Harrison Chase 博文 (2025.10)
