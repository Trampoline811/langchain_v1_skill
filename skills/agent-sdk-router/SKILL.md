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

## 竞品对标

| 层级 | LangChain 系 | 其他 |
|------|-------------|------|
| Framework | LangChain | AI SDK, LlamaIndex, CrewAI, Google ADK, OpenAI Agents SDK |
| Runtime | LangGraph | Temporal, Inngest |
| Harness | DeepAgents | Claude Agent SDK |

## 执行协议

1. **先问关键问题**：需要开箱即用的文件系统/子Agent/规划吗？→ DeepAgents；需要自己设计图拓扑或底层持久化？→ LangGraph；以上都不需要，快速标准 Agent？→ LangChain
2. **确认后跳转**：`/langchain-v1` 或 `/langgraph-v1` 或 `/deepagents-v1`
3. **不知道时默认**：LangChain `create_agent()` — 大部分场景足够
