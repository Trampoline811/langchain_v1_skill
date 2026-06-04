# deepagents-v1 更新日志

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
