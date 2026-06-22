# langchain-v1 更新日志

## 2026-06-22 (AgentSeek 社区 skill 对标更新)

- **新增** `references/cn-model-integration.md` — 国产模型集成指南（DeepSeek/Qwen/GLM/Moonshot）：ChatOpenAI 直连三大坑、两种修复方案、推理模型路由、生产 Checklist
- **新增** `references/common-pitfalls.md` — 高频踩坑合集：工具返回值三通道语义、`with_structured_output` 返回 None 三级修复、MCP context 访问、流式常见坑、洋葱模型、`wrap_model_call` state 修改
- **增强** `references/api-reference.md` — 中间件执行顺序（洋葱模型）+ `[社区]` 交叉引用
- **增强** `references/patterns.md` — 流式最佳实践（v2/v3 对比、自定义进度事件）+ Subagents vs Handoffs 决策表
- **更新** `SKILL.md` — 执行协议新增 §9-11 + 模型节新增国产模型交叉引用 + LangSmith 交叉引用独立 skill
- **新增** `skills/langsmith-trace/` — 独立 skill（SKILL.md + reference/cli-commands.md + CHANGELOG.md），跨三层观测排障
- **来源** AgentSeek `skills/langchain-dev-guide/` + `skills/langsmith-trace/` (ob-labs/agentseek)，社区工程踩坑经验

## 2026-06-14 (Step 5b — 官方文档同步)

- **更新** 模型版本字符串: `gpt-5.4` → `gpt-5.5` (全局替换，对齐 docs.langchain.com 最新版)
- **新增** §5.1 中间件速查表 5 个新条目: `ShellToolMiddleware`（持久化 shell）、`FilesystemFileSearchMiddleware`（Glob+Grep）、`ProviderToolSearchMiddleware`（服务端工具搜索）、`LLMToolSelectorMiddleware`（LLM 预选工具）、`ToolCallLimitMiddleware`（限制工具调用次数）
- **新增** §5.2 Shell 与 File Search 示例（`HostExecutionPolicy` + `use_ripgrep`）
- **新增** §5.3 钩子速查一行（`@before_model → @wrap_model_call → @after_model`）
- **章节重编号** 5.2→5.3（自定义中间件），5.3→5.4（进阶中间件模式）
- **来源** 196 个官方 .mdx 文件全量同步，51 个内容变更文件 diff 分析 (docs.langchain.com, 2026-06-14)

## 2026-06-14 (第二次更新)

- **新增** §5.3 进阶中间件模式：before_model 上下文注入/消息裁剪、wrap_model_call 动态路由/重试熔断、after_model 输出校验，所有示例来自社区实战验证
- **新增** §13 部署与运维：LangSmith/LangGraph Studio/LangGraph CLI 工具套件速查 + FastAPI 部署模板 + 生产依赖清单
- **新增** §14 社区案例速查：5 个实战案例索引表 + Part 1~6 教程系列导航
- **来源** 社区文档 `docs/community/cases/` (5个案例) + `docs/community/patterns/` (Part 1~6 系列教程)

## 2026-06-14

- **新增** 定位章节：LangChain 官方定义的 Agent Framework / Runtime / Harness 三层关系图，标注关键架构事实"LangChain 1.0 的 agent loop 跑在 LangGraph runtime 之上"
- **新增** agent-sdk-router 交叉引用（定位章节末尾）
- **来源** Harrison Chase 官方博文 "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

## 2026-06-02

- **初始创建** 基于 LangChain v1.0 官方文档提炼，覆盖黑名单、模型初始化、Agent 创建、Middleware 体系、多 Agent、流式、记忆、HITL、结构化输出、生产部署（~500 行）
