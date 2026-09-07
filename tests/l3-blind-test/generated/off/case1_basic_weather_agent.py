import os
from typing import Optional, Type

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI


# ---------- 工具定义 ----------
class WeatherInput(BaseModel):
    city: str = Field(description="城市名称，例如：北京、上海、广州")


class GetWeatherTool(BaseTool):
    """查询指定城市的天气信息（模拟数据）"""

    name: str = "get_weather"
    description: str = (
        "查询指定城市的当前天气情况。输入应为城市名称（中文或英文均可）。"
        "例如：'北京'、'Shanghai'。"
    )
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, city: str) -> str:
        # 模拟天气数据，实际项目中可替换为真实 API 调用
        weather_map = {
            "北京": "晴，25°C，微风",
            "上海": "多云，28°C，东南风3级",
            "广州": "雷阵雨，30°C，南风2级",
            "深圳": "阴，29°C，无持续风向",
            "杭州": "小雨，24°C，东北风2级",
        }
        # 支持英文城市名映射
        en_map = {
            "beijing": "北京",
            "shanghai": "上海",
            "guangzhou": "广州",
            "shenzhen": "深圳",
            "hangzhou": "杭州",
        }
        normalized = city.strip().lower()
        if normalized in en_map:
            city_cn = en_map[normalized]
        else:
            city_cn = city.strip()

        if city_cn in weather_map:
            return f"{city_cn}：{weather_map[city_cn]}"
        else:
            return f"抱歉，暂未收录 {city_cn} 的天气数据。"


# ---------- 模型初始化 ----------
def init_llm() -> ChatOpenAI:
    """初始化大语言模型（使用 OpenAI 兼容接口）"""
    # 请确保已设置 OPENAI_API_KEY 环境变量，或在此处直接传入
    api_key = os.getenv("OPENAI_API_KEY", "sk-your-key-here")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key,
        base_url=base_url,
    )


# ---------- Agent 构建 ----------
def build_agent(llm: ChatOpenAI) -> AgentExecutor:
    """构建天气查询 Agent"""
    tools = [GetWeatherTool()]

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=(
                    "你是一个天气查询助手。当用户询问某个城市的天气时，"
                    "你必须调用 get_weather 工具来获取信息。"
                    "如果用户没有明确指定城市，请主动询问。"
                )
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
    )
    return executor


# ---------- 主入口 ----------
if __name__ == "__main__":
    # 初始化模型与 Agent
    llm = init_llm()
    agent_executor = build_agent(llm)

    # 单轮示例调用
    result = agent_executor.invoke(
        {
            "input": "请问北京今天天气怎么样？",
            "chat_history": [],
        }
    )
    print("\n=== 最终回答 ===")
    print(result["output"])