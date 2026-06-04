# langgraph-v1 更新日志

## 2026-06-04

- **新增** §11 设计模式（GraphConfig 按节点选模型 / RemoveMessage 语境窗口管理 / 多阶段质量环），来源 langgraph-engineer (hwchase17, Aug 2024)，提取其中与 API 版本无关的工程实践

## 2026-06-02

- **初始创建** 基于 LangGraph 官方文档 25 个 langgraph-*.md 文件提炼，覆盖 Graph API、Functional API、持久化（3 种 Checkpointer）、流式输出、HITL 中断恢复、子图、容错 RetryPolicy、选型决策表、执行协议 10 个章节（261 行）
