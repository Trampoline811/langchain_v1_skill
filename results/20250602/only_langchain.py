"""
天气查询 Agent — 仅使用 langchain（不额外引入其他库）

安装: pip install langchain[openai]
说明: langchain 1.x 的 create_agent 内部基于 LangGraph，
      但用户只需安装 langchain 这一个包即可，LangGraph 会作为依赖自动安装。
      所有 import 均来自 langchain / langchain_core / langgraph.checkpoint，
      即 langchain 的自带子包，无需额外安装第三方库。
"""

from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver


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


# ── 2. 创建 Agent ────────────────────────────────────────────
# create_agent 直接接收 "provider:model" 字符串，无需手动初始化模型
# 内部会通过 init_chat_model 自动解析并创建对应的 Chat Model
agent = create_agent(
    "openai:gpt-4o",
    tools=[get_weather],
    system_prompt="你是一个专业的天气查询助手。当用户询问城市天气时，调用 get_weather 工具获取信息，然后用自然语言回复。如果用户问的城市不在数据库中，也要友好地告知。",
    checkpointer=InMemorySaver(),
)

# ── 3. 运行测试 ──────────────────────────────────────────────
import uuid

config = {"configurable": {"thread_id": str(uuid.uuid4())}}

print("=" * 60)
print("  天气查询 Agent — 仅使用 langchain")
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

# ── 4. 流式输出 ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("  流式输出演示")
print("=" * 60)
print(f"\n👤 用户: 对比一下北京和成都的天气")
print("🤖 助手: ", end="")

config_stream = {"configurable": {"thread_id": str(uuid.uuid4())}}
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

# ── API 清单 ─────────────────────────────────────────────────
print("=" * 60)
print("  依赖清单（仅需 pip install langchain[openai]）")
print("=" * 60)
print("  ✅ langchain.agents.create_agent  → Agent 创建")
print("  ✅ langchain.tools.@tool          → 工具定义")
print("  ✅ langgraph.checkpoint.memory    → 对话记忆（langchain 自带依赖）")
print("  ✅ openai:gpt-4o 模型字符串       → 模型指定（无需 langchain-openai）")
print("  ❌ 无其他第三方库")
