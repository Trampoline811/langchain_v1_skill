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
    """模拟天气查询工具（实际可替换为真实 API）"""
    name: str = "get_weather"
    description: str = "查询指定城市的当前天气情况"
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, city: str) -> str:
        # 模拟数据，实际可替换为真实天气 API 调用
        weather_map = {
            "北京": "晴，25°C，微风",
            "上海": "多云，28°C，东南风3级",
            "广州": "雷阵雨，30°C，南风2级",
            "深圳": "阴，29°C，西南风2级",
        }
        return weather_map.get(city, f"抱歉，暂时没有{city}的天气数据，请尝试其他城市。")


# ---------- 模型初始化 ----------
def init_model() -> ChatOpenAI:
    """初始化 LLM 模型（使用 OpenAI 兼容接口）"""
    api_key = os.getenv("OPENAI_API_KEY", "sk-your-key")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )


# ---------- Agent 构建 ----------
def build_agent(model: ChatOpenAI) -> AgentExecutor:
    """构建带天气工具的 Agent"""
    tools = [GetWeatherTool()]

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content="你是一个天气查询助手，请根据用户输入的城市名，调用工具查询天气。"),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(model, tools, prompt)
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
    # 初始化模型
    llm = init_model()

    # 构建 Agent
    agent_executor = build_agent(llm)

    # 单轮示例调用
    result = agent_executor.invoke(
        {
            "input": "请问北京今天天气怎么样？",
            "chat_history": [],
        }
    )
    print("\n最终回答：", result["output"])