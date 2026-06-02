"""
天气查询 Agent — 纯 LangChain 0.x 写法

约束:
  - pip install langchain langchain-openai  （langchain-openai 是 langchain 的官方子包）
  - 不使用 LangGraph
  - 不使用 LangChain 1.0 的 create_agent（其内部依赖 LangGraph）
  - 使用经典 AgentExecutor + create_react_agent 写法
"""

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain import hub
from langchain_core.prompts import PromptTemplate


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
llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
tools = [get_weather]

# ── 3. 构建 ReAct Agent ─────────────────────────────────────
# 方式 A: 从 LangChain Hub 拉取标准 ReAct prompt
# prompt = hub.pull("hwchase17/react")

# 方式 B: 手动定义 ReAct prompt（更可控，不依赖网络）
prompt = PromptTemplate.from_template(
    """你是一个专业的天气查询助手。

你可以使用以下工具:
{tools}

使用工具时，请严格按以下格式:
Question: 用户的问题
Thought: 你应该思考做什么
Action: 要使用的工具名（必须是 [{tool_names}] 中的一个）
Action Input: 工具的输入参数
Observation: 工具的返回结果
... (Thought/Action/Action Input/Observation 可以重复)
Thought: 我现在知道最终答案了
Final Answer: 最终回答

开始!

Question: {input}
Thought:{agent_scratchpad}"""
)

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# ── 4. 运行测试 ──────────────────────────────────────────────
print("=" * 60)
print("  天气查询 Agent — 纯 LangChain（无 LangGraph）")
print("=" * 60)

# 第一轮
print("\n👤 用户: 北京今天天气怎么样？")
print("-" * 40)
r1 = agent_executor.invoke({"input": "北京今天天气怎么样？"})
print(f"🤖 最终回答: {r1['output']}")

# 第二轮
print("\n👤 用户: 深圳的天气如何？")
print("-" * 40)
r2 = agent_executor.invoke({"input": "深圳的天气如何？"})
print(f"🤖 最终回答: {r2['output']}")

# 第三轮：不存在的城市
print("\n👤 用户: 帮我看看拉萨的天气")
print("-" * 40)
r3 = agent_executor.invoke({"input": "帮我看看拉萨的天气"})
print(f"🤖 最终回答: {r3['output']}")

# ── 依赖清单 ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  依赖清单")
print("=" * 60)
print("  pip install langchain langchain-openai")
print()
print("  ✅ langchain_openai.ChatOpenAI    → 模型")
print("  ✅ langchain.agents.create_react_agent → Agent 创建")
print("  ✅ langchain.agents.AgentExecutor → Agent 执行器")
print("  ✅ langchain.tools.@tool          → 工具定义")
print("  ✅ langchain_core.prompts         → Prompt 模板")
print("  ❌ LangGraph — 未使用")
print("  ❌ 其他第三方库 — 未使用")
