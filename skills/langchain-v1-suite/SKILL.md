---
name: langchain-v1-suite
description: LangChain v1.0 全家桶入口。覆盖 Agent Framework/Runtime/Harness/Observability 四层。写 LangChain 代码、构建 Agent、选型决策、调试 Trace 时激活。触发词：langchain、agent、create_agent、langgraph、StateGraph、deepagents、langsmith、trace、选型、构建智能体。
---

# LangChain v1.0 Skill Suite

> LangChain 2025.11 进入 1.0，API 根本变化。本 skill 是**层级入口**——先路由到正确的产品层，再按需加载子技能获取完整编码规范。
> 来源：Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

## 三层架构

```
LangChain v1.0 Skill Suite（本入口）
    │
    ├── langchain-v1   ← Agent Framework（create_agent, @tool, middleware）
    │                     ⚠️ agent loop 跑在 LangGraph runtime 之上
    │
    ├── langgraph-v1   ← Agent Runtime（StateGraph, persistence, HITL, streaming）
    │                    durable execution / 自定义图拓扑 / 持久化
    │
    ├── deepagents-v1  ← Agent Harness（规划 + 文件系统 + 子Agent + 记忆 全部内置）
    │                    create_deep_agent() — 预组装电池包
    │
    └── langsmith-trace ← Observability（跨层观测排障）
                          CLI trace 查询 / 5 步排障 / Trace 树解读
```

## 路由决策

### 决策表

| 你想… | 用 | 因为 |
|--------|-----|------|
| 快速开始，团队标准化构建 | **LangChain** | Agent Framework — 标准抽象（`create_agent`/`@tool`/`middleware`） |
| 底层控制图拓扑，长运行有状态 Agent | **LangGraph** | Agent Runtime — durable execution / streaming / HITL / persistence |
| 自主型 Agent，开箱即用（文件系统/子Agent/规划） | **DeepAgents** | Agent Harness — 预装工具、prompts、subagents |
| 调试 Agent 行为、Trace 排障、加观测 | **LangSmith Trace** | Observability — CLI trace 查询、5 步排障、IO 检查 |

### 场景对照

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

### 竞品对标

| 层级 | LangChain 系 | 其他 |
|------|-------------|------|
| Framework | LangChain | AI SDK, LlamaIndex, CrewAI, Google ADK, OpenAI Agents SDK |
| Runtime | LangGraph | Temporal, Inngest |
| Harness | DeepAgents | Claude Agent SDK |

## 子技能索引

> **加载方式**：根据路由决策匹配子技能后，`read_file` 对应路径获取完整编码规范。**不要一次性全部加载。**

| 子技能 | 用途 | 触发关键词 | 文件路径 |
|--------|------|-----------|----------|
| **langchain-v1** | Agent Framework 代码生成规范 | `create_agent`, `@tool`, `middleware`, `init_chat_model`, `checkpointer`, structured output, streaming | `skills/langchain-v1-suite/langchain-v1/SKILL.md` |
| **langgraph-v1** | Agent Runtime 底层编排规范 | `StateGraph`, `functional API`, `persistence`, `interrupts`, `subgraphs`, `checkpointer` | `skills/langchain-v1-suite/langgraph-v1/SKILL.md` |
| **deepagents-v1** | Agent Harness 开箱即用规范 | `create_deep_agent`, `sandbox`, `文件系统`, `子Agent`, `深度研究`, `内容构建` | `skills/langchain-v1-suite/deepagents-v1/SKILL.md` |
| **langsmith-trace** | Observability 观测排障规范 | `trace`, `tracing`, `debug agent`, `LangSmith`, `慢请求` | `skills/langchain-v1-suite/langsmith-trace/SKILL.md` |

## 执行协议

1. **先查场景对照表** — 上面两个表覆盖 90% 场景
2. **路由到子技能** — `read_file` 加载对应子技能 SKILL.md 获取完整规范
3. **不知道时默认** — LangChain `create_agent()`，大部分场景足够，不够了无缝降级
4. **可以混用** — 顶层用 DeepAgents 快速搭建，底层用 LangGraph 做精细化控制
5. **线上出问题先查 Trace** — 加载 langsmith-trace，5 步排障定位根因
6. **子技能内含 references/** — 需要详细 API 签名、迁移指南、模式参考时，子技能 SKILL.md 会指引进一步 `read_file` 其 references/ 下的文件

## 核心约束

- **当前项目为唯一真相源** — `skills/` 是唯一编辑点
- **只用 v1.0 API** — `create_agent()` / `init_chat_model()` / `@tool` / `middleware` / `checkpointer`
- **禁用旧版** — `AgentExecutor` / `ChatOpenAI()` / `LLMChain` / `ConversationBufferMemory` 全部禁止
