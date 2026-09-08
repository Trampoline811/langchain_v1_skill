import os
from typing import Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.utils.uuid import uuid7


# ---------------------------------------------------------------------------
# 工具定义（模块级，仅定义不初始化模型）
# ---------------------------------------------------------------------------
@tool
def remember_user_preference(
    key: str, value: str, runtime: ToolRuntime
) -> str:
    """Store a user preference (e.g. name, favorite color, language).
    Use this whenever the user shares a personal detail you should remember."""
    namespace = ("user_prefs",)
    user_id = runtime.context.user_id
    prefs = runtime.store.get(namespace, user_id)
    if prefs is None:
        prefs = {}
    prefs[key] = value
    runtime.store.put(namespace, user_id, prefs)
    return f"Saved preference: {key} = {value}"


@tool
def get_user_preferences(runtime: ToolRuntime) -> str:
    """Retrieve all stored preferences for the current user."""
    namespace = ("user_prefs",)
    user_id = runtime.context.user_id
    prefs = runtime.store.get(namespace, user_id)
    if prefs is None:
        return "No preferences stored yet."
    return ", ".join(f"{k}={v}" for k, v in prefs.items())


# ---------------------------------------------------------------------------
# 模型初始化（独立函数）
# ---------------------------------------------------------------------------
def init_model():
    """Initialize and return the chat model."""
    load_dotenv()
    model_name = os.getenv("MODEL_NAME", "openai:gpt-4o-mini")
    return init_chat_model(model_name, temperature=0.3)


# ---------------------------------------------------------------------------
# Agent 构建（独立函数）
# ---------------------------------------------------------------------------
def build_agent():
    """Build and return the customer-service agent."""
    model = init_model()
    checkpointer = InMemorySaver()
    store = InMemoryStore()

    system_prompt = (
        "You are a friendly customer-service assistant. "
        "Use the provided tools to remember and retrieve user preferences. "
        "When the user tells you their name or any preference, save it. "
        "Always greet returning users by name and reference their saved preferences."
    )

    agent = create_agent(
        model=model,
        tools=[remember_user_preference, get_user_preferences],
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        store=store,
    )
    return agent


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    agent = build_agent()
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id, "user_id": "alice"}}

    # 第一轮：用户告知姓名与偏好
    result1 = agent.invoke(
        {"messages": [{"role": "user", "content": "Hi, my name is Alice and I prefer tea over coffee."}]},
        config=config,
    )
    print("Bot:", result1["messages"][-1].content)
    print("-" * 60)

    # 第二轮：同一会话，测试短期记忆
    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "What is my name?"}]},
        config=config,
    )
    print("Bot:", result2["messages"][-1].content)
    print("-" * 60)

    # 第三轮：新会话（同一 user_id），测试长期记忆
    new_thread = str(uuid7())
    new_config = {"configurable": {"thread_id": new_thread, "user_id": "alice"}}
    result3 = agent.invoke(
        {"messages": [{"role": "user", "content": "Do you remember my drink preference?"}]},
        config=new_config,
    )
    print("Bot:", result3["messages"][-1].content)