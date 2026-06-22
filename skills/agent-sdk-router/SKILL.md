---
name: agent-sdk-router
description: Agent SDK 选型路由。当用户说"构建智能体""写 Agent""用哪个库""LangChain vs LangGraph vs DeepAgents""Agent 选型"时，先激活此 skill 做三选一判断，再跳转到对应子 skill。触发词：构建智能体、写Agent、用哪个、选型、LangChain还是LangGraph、DeepAgents。
---

# Agent SDK 选型路由

> 三个包都是 LangChain 官方维护，定位不同。来源：Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

## 决策表

| 你想… | 用 | 因为 |
|--------|-----|------|
| 快速开始，团队标准化构建 | **LangChain** | Agent Framework — 标准抽象（`create_agent`/`@tool`/`middleware`） |
| 底层控制图拓扑，长运行有状态 Agent | **LangGraph** | Agent Runtime — durable execution / streaming / HITL / persistence |
| 自主型 Agent，开箱即用（文件系统/子Agent/规划） | **DeepAgents** | Agent Harness — 预装工具、prompts、subagents |
| 调试 Agent 行为、Trace 排障、加观测 | **LangSmith Trace** | Observability — CLI trace 查询、5 步排障、IO 检查 |

## 竞品对标

| 层级 | LangChain 系 | 其他 |
|------|-------------|------|
| Framework | LangChain | AI SDK, LlamaIndex, CrewAI, Google ADK, OpenAI Agents SDK |
| Runtime | LangGraph | Temporal, Inngest |
| Harness | DeepAgents | Claude Agent SDK |

## 场景对照

> 不确定用哪个？对照你的实际需求查表：

| 你的场景 | 用 | 为什么 |
|---------|-----|------|
| "帮我写个 Agent 调几个 API" | LangChain | 标准 tool-calling，create_agent() 一行搞定 |
| "帮我搭个客服机器人，接知识库" | LangChain | create_agent + @tool + RAG |
| "需要上传 CSV 自动分析画图" | **DeepAgents** | 文件系统 + 代码执行沙箱内置 |
| "需要审核 PDF 合同，多步流程+人工审批" | **DeepAgents** | 子Agent + HITL 中断 + 文件系统 |
| "需要自定义复杂图拓扑，平台级产品" | **LangGraph** | 完全控制图结构、持久化、并发 |
| "已有 LangGraph 基础设施，要加 agent" | **LangChain** | create_agent() 底层就是 LangGraph |
| "需要多个 Agent 并行处理不同任务" | **DeepAgents** | SubAgentMiddleware 开箱即用 |
| "Agent 行为异常，不知道它内部怎么决策的" | **LangSmith Trace** | 5 步排障工作流，查 LLM 调用/tool 调用 IO |
| "不确定，快速验证想法" | **LangChain** | 最简单，不够再升级 |

> 完整案例见各 skill 的「社区案例」章节。

## 执行协议

1. **先查场景对照表** — 上面的表格覆盖 90% 场景
2. **确认后跳转**：`/langchain-v1` 或 `/langgraph-v1` 或 `/deepagents-v1` 或 `/langsmith-trace`
3. **不知道时默认**：LangChain `create_agent()` — 大部分场景足够，底层是 LangGraph，不够了无缝降级
4. **可以在一个项目混用**：顶层用 DeepAgents 快速搭建，底层用 LangGraph 做精细化控制
5. **线上出问题先查 Trace**：`/langsmith-trace` — 5 步排障定位根因
