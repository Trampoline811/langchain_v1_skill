# LangChain v0.x → v1.0 完整对照

> **来源**: 官方 `migrate/langchain-v1.md` + 社区旧项目迁移经验
> **定位**: 供面试复习和旧项目迁移参考。
> **文中标记**: `[官方]` = 官方迁移指南 | `[社区]` = 社区迁移实战验证

## 从旧版 RAG 到新版 Agent

**旧版（v0.x，你写过的）：**
```python
# 加载 → 切分 → 向量化 → 入库 → 检索 → 用链组合 → 生成
loader = TextLoader("doc.txt")
chunks = RecursiveCharacterTextSplitter().split_documents(loader.load())
vectorstore = Chroma.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever()
qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
qa.run("问题")
```

**新版（v1.0，Agent 驱动）：**
```python
@tool
def search_docs(query: str) -> str:
    """搜索知识库中的相关文档"""
    docs = vectorstore.similarity_search(query, k=3)
    return "\n---\n".join([d.page_content for d in docs])

agent = create_agent(
    model="openai:gpt-5.4",
    tools=[search_docs],
    system_prompt="用 search_docs 查找信息后回答。"
)
result = agent.invoke({"messages": [{"role": "user", "content": "问题"}]})
```

**关键区别：** 旧版是你规定"先检索再生成"。新版 Agent 自己决定要不要检索、搜什么、搜几次。

## 完整 API 对照表

| v0.x | v1.0 | 类型 |
|------|------|:--:|
| `LLMChain(llm, prompt)` | `model.invoke()` 或 `create_agent()` | 删除 |
| `ConversationChain(llm)` | `create_agent(model, checkpointer=...)` | 重做 |
| `load_summarize_chain` | `SummarizationMiddleware(model=...)` | 重做 |
| `RetrievalQA.from_chain_type` | `create_agent(model, tools=[retriever_tool])` | 重做 |
| `ConversationBufferMemory` | `checkpointer=InMemorySaver()` + `thread_id` | 重做 |
| `AgentExecutor(agent, tools)` | `create_agent(model, tools)` | 合并 |
| `create_react_agent` | `create_agent` | 改名 |
| `ChatOpenAI(model="gpt-4")` | `init_chat_model("openai:gpt-4")` | 统一 |
| `Tool.from_function()` | `@tool` 装饰器 | 简化 |
| `InjectedState / InjectedStore` | `runtime: ToolRuntime` | 统一 |
| `from langchain.chains import LLMChain` | `from langchain_classic.chains import LLMChain` | 归档 |
| `NodeInterrupt` | `GraphInterrupt` | 改名 |
| `Command(goto=...)` | `Command(graph=...)` | 改名 |
| `InjectedState` (Pydantic) | `state_schema=CustomAgentState` | 统一 |
| `BaseStore` 手动管理 | `store=InMemoryStore()` | 统一 |

## Agent State 迁移

v0 中通过 `StateGraph(State)` 手动定义 state。v1 中 `create_agent` 内置了 messages state，只需通过 `state_schema` 扩展：

```python
# v0 (旧)
from langgraph.graph import StateGraph, MessagesState
builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
graph = builder.compile()

# v1 (新)
from langchain.agents import AgentState, create_agent
class CustomState(AgentState):
    user_name: str = ""
agent = create_agent(model, tools, state_schema=CustomState)
```

## LangGraph v1 改动（极简）

- `StateGraph`, `add_node`, `add_edge`, `add_conditional_edges`, `compile` → **全部保留**
- `NodeInterrupt` → `GraphInterrupt`
- `Command(goto="node_name")` → `Command(graph=Command.PARENT)`
- Stream v2 格式 → 返回 `(mode, chunk)` 元组
- `invoke()` 返回 `GraphOutput`（含 `.value` 和 `.interrupts`）
- Python 3.10+

## v1 的核心哲学

**不是换了 API，是换了思想：**

| 旧版思维 | 新版思维 |
|---------|---------|
| "我要把 prompt、模型、输出解析器串起来" | "我定义一个 Agent，告诉他有什么工具、什么风格" |
| 开发者决定执行顺序 | Agent 决定执行顺序 |
| 链是结构（编译时固定） | 中间件是行为（运行时插入） |
| 框架帮你拼积木 | 框架帮你管理 Agent 行为 |
