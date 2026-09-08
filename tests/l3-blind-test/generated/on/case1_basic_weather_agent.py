import os
from typing import Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a given city."""
    # In a real application, you would call a weather API here.
    # This is a mock implementation for demonstration purposes.
    weather_data = {
        "北京": "晴，25°C",
        "上海": "多云，28°C",
        "广州": "雷阵雨，30°C",
        "深圳": "阴，29°C",
        "杭州": "小雨，26°C",
    }
    return weather_data.get(city, f"抱歉，没有找到 {city} 的天气数据。")


def initialize_model() -> object:
    """Initialize and return the chat model."""
    # Load environment variables from .env file if present
    load_dotenv()

    # Use environment variable or default to a common model
    model_name = os.getenv("MODEL_NAME", "openai:gpt-4o-mini")

    # Initialize the model
    model = init_chat_model(model_name, temperature=0.1)
    return model


def build_agent(model: object) -> object:
    """Build and return the weather agent."""
    agent = create_agent(
        model=model,
        tools=[get_weather],
        system_prompt=(
            "You are a helpful weather assistant. "
            "When the user asks about the weather in a city, "
            "use the get_weather tool to fetch the information."
        ),
    )
    return agent


if __name__ == "__main__":
    # Initialize model
    chat_model = initialize_model()

    # Build agent
    weather_agent = build_agent(chat_model)

    # Single-turn example invocation
    result = weather_agent.invoke(
        {"messages": [{"role": "user", "content": "北京今天天气怎么样？"}]}
    )

    # Print the final response
    print(result["messages"][-1].content)