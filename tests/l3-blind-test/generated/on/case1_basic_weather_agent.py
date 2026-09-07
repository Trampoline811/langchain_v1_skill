import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

# Load environment variables (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY)
load_dotenv()


class WeatherInput(BaseModel):
    """Input schema for the get_weather tool."""
    city: str = Field(description="The name of the city to get weather for.")


@tool(args_schema=WeatherInput)
def get_weather(city: str) -> str:
    """Get the current weather for a specified city."""
    # In a real application, this would call a weather API.
    # Here, we simulate a response.
    weather_data = {
        "北京": "晴，25°C",
        "上海": "多云，28°C",
        "广州": "雷阵雨，30°C",
        "深圳": "晴，29°C",
        "New York": "Partly cloudy, 22°C",
        "London": "Rainy, 15°C",
        "Tokyo": "Clear, 27°C",
    }
    # Default response if city not found
    default_weather = "晴，20°C"
    return f"{city}的天气：{weather_data.get(city, default_weather)}"


def initialize_model() -> object:
    """
    Initialize and return the chat model.
    Uses the init_chat_model function for provider-agnostic setup.
    """
    # You can change the model string to use different providers/models.
    # Examples: "openai:gpt-4o", "claude-sonnet-4-6", "google_genai:gemini-1.5-pro"
    model_name = os.getenv("MODEL_NAME", "openai:gpt-4o")
    model = init_chat_model(model_name, temperature=0.1)
    return model


def build_weather_agent(model: object):
    """
    Build and return the weather query agent.
    """
    agent = create_agent(
        model=model,
        tools=[get_weather],
        system_prompt="You are a helpful weather assistant. "
                      "When the user asks about the weather in a city, "
                      "use the 'get_weather' tool to find the information.",
    )
    return agent


if __name__ == "__main__":
    # --- Model Initialization ---
    chat_model = initialize_model()

    # --- Agent Construction ---
    weather_agent = build_weather_agent(chat_model)

    # --- Single-turn example invocation ---
    user_query = "北京今天天气怎么样？"
    print(f"User: {user_query}")

    result = weather_agent.invoke(
        {"messages": [{"role": "user", "content": user_query}]}
    )

    # Extract and print the final response
    response = result["messages"][-1].content
    print(f"Agent: {response}")