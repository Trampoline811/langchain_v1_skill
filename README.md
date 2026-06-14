# LangChain v1.0 Skill Suite

为 LLM 提供 LangChain 生态编码规范的 Claude Code Skill 合集。
覆盖 Agent Framework / Runtime / Harness 三层 + 选型路由。

## 盲测结果

| 条件 | 得分 | 根本原因 |
|------|:--:|------|
| Skill ON | 10/10 | API 全对 |
| Skill OFF | 0/10 | 离线的 LLM 用 2023 年的 v0.x API（`AgentExecutor` + `ChatOpenAI` + `create_react_agent`） |

## Skill 目录

| Skill | 层级 | 行数 | 用途 | 什么时候加载 |
|-------|------|:--:|------|------------|
| [agent-sdk-router](skills/agent-sdk-router/SKILL.md) | 入口 | 30 | 三选一决策表 → 跳转子 skill | 用户说"构建智能体""选哪个库" |
| [langchain-v1](skills/langchain-v1/SKILL.md) | Framework | 426 | `create_agent` / `@tool` / `middleware` / `checkpointer` | 写 LangChain agent 代码 |
| [langgraph-v1](skills/langgraph-v1/SKILL.md) | Runtime | 362 | `StateGraph` / `Functional API` / persistence / HITL / subgraphs | 需要图编排/持久化/中断 |
| [deepagents-v1](skills/deepagents-v1/SKILL.md) | Harness | 560 | 文件系统 / 子Agent / 规划 / 上下文管理 / 异步 | 复杂多步任务、预组装 agent |

## 三层架构

> 术语来源：Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)

```
agent-sdk-router   ← 入口决策：Framework / Runtime / Harness？
    │
    ├── langchain-v1   ← Agent Framework（抽象层，标准心智模型）
    │                     LangChain 1.0 的 agent loop 跑在 LangGraph runtime 之上
    │
    ├── langgraph-v1   ← Agent Runtime（基础设施层）
    │                     durable execution / streaming / HITL / persistence
    │                     "both a runtime and a framework" — Harrison Chase
    │
    └── deepagents-v1  ← Agent Harness（预组装电池包）
                          规划 + 文件系统 + 子Agent + 记忆 全部内置
```

## 竞品对标

| 层级 | LangChain 系 | 其他 |
|------|-------------|------|
| Framework | LangChain | AI SDK, LlamaIndex, CrewAI, Google ADK, OpenAI Agents SDK |
| Runtime | LangGraph | Temporal, Inngest |
| Harness | DeepAgents | Claude Agent SDK |

## 安装

复制 `skills/` 下需要的目录到你的 skill 目录：

```json
{
  "skillOverrides": {
    "agent-sdk-router": "on",
    "langchain-v1": "on",
    "deepagents-v1": "user-invocable-only",
    "langgraph-v1": "user-invocable-only"
  }
}
```

## 选型速查

| 你想… | 用 |
|--------|-----|
| 快速开始，团队标准化 | **LangChain** `create_agent()` |
| 底层控制图拓扑，长运行有状态 | **LangGraph** `StateGraph` |
| 自主型 Agent，开箱即用 | **DeepAgents** `create_deep_agent()` |
| 不知道该用哪个 | `/agent-sdk-router` |

## 更新日志

每个 skill 有独立的 `CHANGELOG.md`：

| Skill | 最近更新 |
|-------|------|
| agent-sdk-router | 2026-06-14 新建 |
| langchain-v1 | 2026-06-14 新增 Framework/Runtime/Harness 定位 + Router 交叉引用 |
| langgraph-v1 | 2026-06-14 更新 Runtime 定位 + 设计模式 §11 (2026-06-05) |
| deepagents-v1 | 2026-06-14 新增 Harness 定位 + 中间件装配 + 异步子Agent (2026-06-04) |

## 维护

```bash
python tools/update_skill.py              # 同步官方文档
python tools/update_skill.py --docs-only  # 只拉文档
python tools/update_skill.py --test-only  # 功能验证
```
