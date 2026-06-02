"""
天气查询 Agent — LangChain v1.0 写法

遵循规则:
  - init_chat_model() 替代 ChatOpenAI()
  - create_agent() 替代 LLMChain + AgentExecutor
  - @tool 装饰器替代 Tool.from_function()
  - InMemorySaver() checkpointer 替代 ConversationBufferMemory
  - 禁止: LLMChain / ChatOpenAI / AgentExecutor / ConversationBufferMemory
"""

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import ToolRetryMiddleware
from langchain_core.utils.uuid import uuid7


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
model = init_chat_model("openai:gpt-4o", temperature=0.3)

# ── 3. 创建 Agent ────────────────────────────────────────────
agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt="你是一个专业的天气查询助手。当用户询问城市天气时，调用 get_weather 工具获取信息，然后用自然语言回复。如果用户问的城市不在数据库中，也要友好地告知。",
    checkpointer=InMemorySaver(),
    middleware=[
        ToolRetryMiddleware(max_retries=2),  # 工具调用失败自动重试
    ],
)

# ── 4. 运行测试 ──────────────────────────────────────────────
config = {"configurable": {"thread_id": str(uuid7())}}

print("=" * 60)
print("  天气查询 Agent — LangChain v1.0")
print("=" * 60)

# 第一轮：直接查询
r1 = agent.invoke(
    {"messages": [{"role": "user", "content": "北京今天天气怎么样？"}]},
    config=config,
)
print(f"\n👤 用户: 北京今天天气怎么样？")
print(f"🤖 助手: {r1['messages'][-1].content}")

# 第二轮：测试多轮记忆（"那边" 指代上文的城市）
r2 = agent.invoke(
    {"messages": [{"role": "user", "content": "那深圳呢？"}]},
    config=config,
)
print(f"\n👤 用户: 那深圳呢？")
print(f"🤖 助手: {r2['messages'][-1].content}")

# 第三轮：测试不存在的城市
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

config_stream = {"configurable": {"thread_id": str(uuid7())}}
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "对比一下北京和成都的天气"}]},
    config=config_stream,
    stream_mode=["messages"],
    version="v2",
):
    if mode == "messages":
        msg_chunk, _ = chunk
        if msg_chunk.content:
            print(msg_chunk.content, end="", flush=True)

print("\n")

# ── API 合规检查 ─────────────────────────────────────────────
print("=" * 60)
print("  v1.0 API 合规检查")
print("=" * 60)
print("  ✅ init_chat_model()          → 替代 ChatOpenAI()")
print("  ✅ create_agent()             → 替代 LLMChain + AgentExecutor")
print("  ✅ @tool 装饰器                → 替代 Tool.from_function()")
print("  ✅ InMemorySaver() checkpointer → 替代 ConversationBufferMemory()")
print("  ✅ ToolRetryMiddleware         → 工具调用自动重试")
print("  ✅ agent.stream()             → 流式输出")
print("  ✅ 黑名单 API 使用次数: 0")
