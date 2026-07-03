# langgraph-v1 更新日志

## 2026-06-14 (Step 5b — 官方文档同步)

- **扩展** §4 持久化: 新增 `AsyncSqliteSaver` / `AsyncPostgresSaver` backend、自定义序列化 `JsonPlusSerializer(pickle_fallback=True)`、`get_state()` / `get_state_history()` API
- **新增** §4.1 Store（长期记忆）: `InMemoryStore` / `PostgresStore`、跨线程 key-value 持久化、语义搜索、`store.put()` / `store.search()` / `store.list_namespaces()` API
- **新增** §4.2 Time Travel: `get_state_history()` 历史重播 + `update_state()` 状态修改后继续执行
- **扩展** §8 容错与超时: 图级别默认重试 `graph.compile(retry=...)`、超时控制（`timeout` + `idle_timeout`）、错误路由（`Command(goto="fallback")`）、重试状态检查 `get_retry_state()`
- **来源** 新增官方文件 `langgraph-stores.md` (631行), `langgraph-checkpointers.md` (1128行), `langgraph-use-time-travel.md`; `langgraph-fault-tolerance.md` 扩展至 1234 行

## 2026-06-14 (第二次更新)

- **新增** §12 社区案例：3 个必须 LangGraph 的实战场景对照表（文档审核/数据分析/全栈Agent），强调 LangGraph 作为所有 Agent 底层 Runtime 的架构事实
- **来源** 社区文档 `docs/community/cases/`

## 2026-06-14

- **更新** 定位章节：统一使用 LangChain 官方 Framework/Runtime/Harness 术语；新增"LangGraph as both runtime and framework"（Harrison 原话）；补注 LangChain 1.0 依赖 LangGraph 的架构事实
- **新增** agent-sdk-router 交叉引用（定位章节末尾）
- **来源** Harrison Chase 官方博文 "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

## 2026-06-04

- **新增** §11 设计模式（GraphConfig 按节点选模型 / RemoveMessage 语境窗口管理 / 多阶段质量环），来源 langgraph-engineer (hwchase17, Aug 2024)，提取其中与 API 版本无关的工程实践

## 2026-06-02

- **初始创建** 基于 LangGraph 官方文档 25 个 langgraph-*.md 文件提炼，覆盖 Graph API、Functional API、持久化（3 种 Checkpointer）、流式输出、HITL 中断恢复、子图、容错 RetryPolicy、选型决策表、执行协议 10 个章节（261 行）
