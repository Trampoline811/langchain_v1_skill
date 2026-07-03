# deepagents-v1 更新日志

## 2026-06-14 (Step 5b — 官方文档同步)

- **大幅扩展** §2.5 技能（Skills）节：新增 Interpreter Skills（可执行 Python 模块）、技能权限系统（shared/limited/read_only/editable）、运行时动态加载（`get_skills(runtime)` 回调）、命名空间技能、子 Agent 专属技能、Sandbox 脚本技能
- **来源** 官方 `deepagents-skills.md` 从 542 行扩展至 1012 行 (+470 行)，遵循 [Agent Skills 规范](https://agentskills.io/specification)

## 2026-06-14 (第二次更新)

- **新增** §10 实战案例速查：全自动数据分析 Agent + 文档审核 Agent 端到端代码示例 + 案例场景对照表
- **来源** 社区文档 `docs/community/cases/`（数据分析Agent、文档审核Agent、mini ChatGPT、OCR PDF）

## 2026-06-14

- **新增** 定位章节：LangChain 官方定义的 Agent Harness 定位；补 Harness/Framework/Runtime 精装房/毛坯房/地基类比；选型边界顶部加官方术语引用
- **新增** agent-sdk-router 交叉引用（定位章节末尾）
- **来源** Harrison Chase 官方博文 "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

## 2026-06-04

- **新增** ⚠️ 选型边界指南（frontmatter 之后）：明确告知 LLM 何时该用/不该用 Deep Agents、何时直接用 LangGraph，附竞品对比表
- **新增** 硅基流动模型配置表（§1）：免费 GLM-4-9B / 推荐 GLM-5、Kimi-K2.5、Qwen3.5、DeepSeek-V3.2
- **扩展** §2.1 文件系统后端：2-backend 表 → 6-backend 完整参考（StateBackend / FilesystemBackend / LocalShellBackend / StoreBackend / CompositeBackend），新增 CompositeBackend 混合路由示例、自定义 BackendProtocol、FilesystemPermission、自动上下文管理机制
- **新增** §2.6 中间件装配架构：三层装配表（常驻层 5 个 / 条件层 5 个 / 用户自定义层），完整中间件全景表，手动组合对照代码
- **扩展** §2.3 子 Agent：3 字段 → 10 字段参考表（含继承规则），新增 General-purpose 覆盖/禁用、CompiledSubAgent、response_format 结构化输出、最佳实践 5 条、排障 3 问
- **新增** §6 异步子 Agent：同步 vs 异步 6 维度对比表，AsyncSubAgent 声明、5 把遥控器工具表、完整生命周期示例、ASGI vs HTTP 传输、3 种部署拓扑、最佳实践 + 排障 4 问
- **翻新** 章节重编号（7→8 决策表、8→9 执行协议），决策表引用顶部选型边界指南
- **来源** 《Deep Agents 实战》课程 6 章（webup/deepagents-course）

## 2026-06-02

- **初始创建** 基于 LangChain v1.0 官方文档 + DeepAgents 文档提炼（276 行），覆盖三层概念图、快速开始、内置能力（文件系统/代码执行/子Agent/记忆/技能）、上下文工程、权限控制、HITL、生产部署、决策表、执行协议
