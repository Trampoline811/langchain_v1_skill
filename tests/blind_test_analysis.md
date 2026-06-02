# 盲测分析报告

## 测试概览

同一 prompt（"天气查询 Agent"），四个不同条件，四份代码。

## 四组完整对照

| 组 | 文件 | 联网 | Skill | 提示词 | 得分 | 关键错误 |
|----|------|:--:|:--:|------|:--:|------|
| A | `only_langchain.py` | ✅ | ❌ | 只用 LangChain | **9/10** | 缺中间件 |
| B | `without_skill_langchain.py` | ❌ | ❌ | LC + LangGraph | **2/10** | ChatOpenAI + 过度工程 |
| C | `with_skill_langchain_v1.py` | ❌ | ✅ | — | **10/10** | 无 |
| **D** | `pure_langchain.py` | ❌ | ❌ | 只用 LangChain | **0/10** | 全部旧版 API |

## 逐份评分

### C 组: `with_skill_langchain_v1.py` — Skill 开启 ⭐10/10

| API | 用法 | 判定 |
|-----|------|:--:|
| 模型初始化 | `init_chat_model("openai:gpt-4o")` | ✅ |
| Agent 创建 | `create_agent(model=model, tools=[...], ...)` | ✅ |
| 工具定义 | `@tool` from `langchain.tools` | ✅ |
| 对话记忆 | `checkpointer=InMemorySaver()` + `thread_id` | ✅ |
| 中间件 | `ToolRetryMiddleware(max_retries=2)` | ✅ |
| 调用方式 | `agent.invoke({"messages": [...]}, config=config)` | ✅ |
| 流式输出 | `agent.stream(... stream_mode=["messages"], version="v2")` | ✅ |
| 旧版 API | **0 处** | ✅ |

**评价**: 完美。5 城市 + 多轮对话 + 流式 + 合规自检。代码清晰有注释。

---

### B 组: `without_skill_langchain.py` — 无 Skill + LangGraph 提示 ⭐2/10

| API | 用法 | 判定 |
|-----|------|:--:|
| 模型初始化 | `ChatOpenAI(model="gpt-4o")` | ❌ 黑名单 |
| Agent 创建 | 手动 `StateGraph` + `agent_node` + `ToolNode` | ❌ 过度设计 |
| 工具绑定 | `.bind_tools(tools)` 预处理 | ❌ 不必要 |
| 对话记忆 | `MemorySaver()` | ⚠️ 可用非推荐 |
| 工具定义 | `@tool` from `langchain_core.tools` | ✅ |
| system_prompt | 手动 `[system_msg] + state["messages"]` | ❌ 应用 `system_prompt=` |
| 旧版 API | **2 处**（ChatOpenAI + 手动 StateGraph） | ❌ |

**评价**: 严重过度工程——一个 `create_agent()` 5 行搞定的事，写了 60 行 StateGraph。"LangGraph 是默认方案"的典型陷阱。

---

### A 组: `only_langchain.py` — 联网搜索 + 自身知识 ⭐9/10

| API | 用法 | 判定 |
|-----|------|:--:|
| Agent 创建 | `create_agent("openai:gpt-4o", ...)` 字符串直接传 | ✅ |
| 工具定义 | `@tool` from `langchain.tools` | ✅ |
| 对话记忆 | `checkpointer=InMemorySaver()` + `thread_id` | ✅ |
| 调用方式 | `agent.invoke({"messages": [...]}, config=config)` | ✅ |
| 流式输出 | `agent.stream(... stream_mode=["messages"], version="v2")` | ✅ |
| 模型初始化 | 无（字符串传给 create_agent） | ✅ 合法 |
| 中间件 | 无 | ⚠️ 但 prompt 没要求 |
| 旧版 API | **0 处** | ✅ |

**评价**: 极简优雅——因为模型搜索到了官方文档。搜索记录显示它访问了 `Agents - Docs by LangChain` 和 `langchain · PyPI`。

---

### D 组: `pure_langchain.py` — 离线 + 无 Skill + 无 LangGraph 提示 🔴0/10

```python
# ===== 黑名单全中 =====
from langchain_openai import ChatOpenAI                    # ❌ 黑名单 #1
from langchain.agents import AgentExecutor, create_react_agent  # ❌ 黑名单 #2-3
from langchain import hub                                  # ❌ LangChain Hub 旧套路

llm = ChatOpenAI(model="gpt-4o", temperature=0.3)          # ❌ 黑名单 #4
agent = create_react_agent(llm, tools, prompt)              # ❌ 黑名单 #5
agent_executor = AgentExecutor(agent=agent, tools=tools)    # ❌ 黑名单 #6
agent_executor.invoke({"input": "..."})                     # ❌ 旧调用方式

# 手动 ReAct prompt 模板 — 2023 年写法
# 无 checkpointer — 无对话记忆
# 无 middleware — 无中间件概念
```

| 黑名单项 | 出现 | 
|----------|:--:|
| `ChatOpenAI` | ✅ |
| `AgentExecutor` | ✅ |
| `create_react_agent` | ✅ |
| `hub.pull("hwchase17/react")` | ⚠️ 注释但存在 |
| `ConversationBufferMemory` | 无（但也没用 checkpointer） |
| `Tool.from_function()` | 无（用了 @tool，仅此一项正确） |

**评价**: **每一行都是黑名单**。LLM 训练数据中残留的 LangChain v0.x 知识原封不动输出。这正是 skill 存在的原因。

---

## 核心发现

### 1. D 组 → C 组的提升是 skill 价值的铁证

```
D (0分) ──加 skill──→ C (10分)    Δ = +10
B (2分) ──加 skill──→ C (10分)    Δ = +8
A (9分) 联网自愈，无需 skill
```

**结论：无互联网 + 无 skill = 必定写出 v0.x 代码。**

### 2. 联网能部分替代 skill

A 组 9 分说明 2026 年的网络上有足够 v1.0 内容。但：
- 离线场景不适用（企业内部 LLM、air-gapped 环境）
- 搜索质量不确定（搜不到=回退到 v0.x）
- 浪费 token 搜索（skill 只需加载 ~5K tokens）

### 3. 训练的 v0.x 残留非常顽固

D 组代码展现了 LLM 对 v0.x 的"肌肉记忆"：
- `AgentExecutor` — 2023 年的核心类
- `create_react_agent` + 手动 prompt 模板 — 旧范式
- ReAct 格式 (`Question/Thought/Action/Observation`) — 手工 prompt engineering
- `agent.invoke({"input": ...})` — 旧输入格式

没有一个 v1.0 API。一个都没有。

### 4. "LangGraph 提示"反而导致过度工程

B 组（提示了 LangGraph）比 D 组（纯 LangChain）得分反而高 2 分，原因：
- B 组虽然用了 ChatOpenAI，但至少走向了 StateGraph（半新半旧）
- D 组完全回退到 2023 年的 ReAct 范式

这验证了 skill 执行协议："先 create_agent，后 LangGraph。"

---

## 对 Skill 的评价

### 已证明有效的部分

| 部分 | 验证证据 |
|------|---------|
| 黑名单 | D 组全中，C 组全避 |
| "先 create_agent，后 LangGraph" | B 组过度工程被纠正 |
| API 签名准确 | C 组所有用法正确 |
| @tool / ToolRuntime | C 组用法无误 |
| checkpointer + thread_id | C 组用法无误 |
| middleware 速查表 | C 组正确使用 ToolRetryMiddleware |
| 流式输出 v2 格式 | C 组正确 |

### 两个微调

| 改进 | 原因 | 优先级 |
|------|------|:--:|
| 开头突出字符串传模型 `create_agent("provider:model", tools=...)` | A 组的最简模式，目前 SKILL.md 更偏向 `init_chat_model` | 低 |
| 加警示"离线环境必须用 skill，不要依赖训练数据" | D 组证明不加 skill = v0.x | 低 |

---

## 结论

**Skill 有效且必要。** 四组盲测完整证明了：

1. LLM 训练数据 = 大量 v0.x（证据：D 组 0/10）
2. 联网 = 能搜到 v1.0 但不可靠（证据：A 组 9/10，但需网络）
3. Skill = 在离线/任何环境下保证 v1.0 正确性（证据：C 组 10/10）
4. 黑名单 + 执行协议是 skill 最核心的两部分
