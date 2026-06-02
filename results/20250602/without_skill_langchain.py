"""
天气查询 Agent — 不使用 skill，按通用知识编写

基于 LangChain + LangGraph 主流写法:
  - ChatOpenAI 初始化模型
  - @tool 装饰器定义工具
  - create_react_agent 创建 Agent
  - MemorySaver 作为 checkpointer 实现对话记忆
"""

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver


# ── 1. 工具定义 ──────────────────────────────────────────────
@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气信息，包括温度、天气状况和建议。"""
    weather_db = {
        "北京": {"temp": 22, "condition": "晴天", "wind": "北风3级", "tip": "适合户外活动"},
        "上海": {"temp": 25, "condition": "多云", "wind": "东南风2级", "tip": "湿度较高，注意防潮"},
        "深圳": {"temp": 28, "condition": "阵雨", "wind": "南风4级", "tip": "记得带伞"},
        "成都": {"temp": 20, "condition": "阴天", "wind": "微风", "tip": "适合吃火锅"},
        "广州": {"temp": 29, "condition": "雷阵雨", "wind": "南风3级", "tip": "注意防雷"},
        "杭州": {"temp": 24, "condition": "晴转多云", "wind": "东风2级", "tip": "温差较大，注意添衣"},
    }
    if city in weather_db:
        w = weather_db[city]
        return f"{city}：{w['condition']}，温度 {w['temp']}°C，{w['wind']}，{w['tip']}"
    return f"{city}：暂无天气数据，请尝试其他城市"


# ── 2. 模型初始化 ────────────────────────────────────────────
tools = [get_weather]
model = ChatOpenAI(model="gpt-4o", temperature=0.3).bind_tools(tools)

# ── 3. 构建 Agent Graph ─────────────────────────────────────
def agent_node(state: MessagesState):
    """调用 LLM 决定是否使用工具"""
    system_msg = {
        "role": "system",
        "content": "你是一个专业的天气查询助手。当用户询问城市天气时，调用 get_weather 工具获取信息，然后用自然语言回复。如果用户问的城市不在数据库中，也要友好地告知。",
    }
    messages = [system_msg] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


# 构建 StateGraph
builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

checkpointer = MemorySaver()
agent = builder.compile(checkpointer=checkpointer)

# ── 4. 运行测试 ──────────────────────────────────────────────
config = {"configurable": {"thread_id": "weather-thread-1"}}

print("=" * 60)
print("  天气查询 Agent — 通用知识写法（无 skill）")
print("=" * 60)

# 第一轮：直接查询
r1 = agent.invoke(
    {"messages": [{"role": "user", "content": "北京今天天气怎么样？"}]},
    config=config,
)
print(f"\n👤 用户: 北京今天天气怎么样？")
print(f"🤖 助手: {r1['messages'][-1].content}")

# 第二轮：测试多轮记忆
r2 = agent.invoke(
    {"messages": [{"role": "user", "content": "那深圳呢？"}]},
    config=config,
)
print(f"\n👤 用户: 那深圳呢？")
print(f"🤖 助手: {r2['messages'][-1].content}")

# 第三轮：不存在的城市
r3 = agent.invoke(
    {"messages": [{"role": "user", "content": "帮我看看拉萨的天气"}]},
    config=config,
)
print(f"\n👤 用户: 帮我看看拉萨的天气")
print(f"🤖 助手: {r3['messages'][-1].content}")

# ── 5. 流式输出演示 ──────────────────────────────────────────
print("\n" + "=" * 60)
print("  流式输出演示")
print("=" * 60)
print(f"\n👤 用户: 对比一下北京和成都的天气")
print("🤖 助手: ", end="")

config_stream = {"configurable": {"thread_id": "weather-stream-1"}}
for msg, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "对比一下北京和成都的天气"}]},
    config=config_stream,
    stream_mode="messages",
):
    if msg.content and isinstance(msg.content, str):
        print(msg.content, end="", flush=True)

print("\n")

# ── API 写法总结 ─────────────────────────────────────────────
print("=" * 60)
print("  通用知识写法 API 清单")
print("=" * 60)
print("  ✅ ChatOpenAI()             → 模型初始化")
print("  ✅ .bind_tools()            → 绑定工具到模型")
print("  ✅ @tool 装饰器              → 工具定义")
print("  ✅ StateGraph(MessagesState) → 手动构建 Agent 图")
print("  ✅ ToolNode + tools_condition → 工具调用节点")
print("  ✅ MemorySaver()            → checkpointer 对话记忆")
print("  ✅ builder.compile()        → 编译可运行 Agent")
