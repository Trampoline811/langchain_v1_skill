from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.utils.uuid import uuid7


@tool
def remember_preference(key: str, value: str, runtime: ToolRuntime) -> str:
    """Remember a user preference. Use when the user tells you their name, or any preference (e.g., language, tone, topic)."""
    runtime.store.put(("user_prefs",), runtime.context.user_id, {key: value})
    return f"Saved preference: {key} = {value}"


@tool
def get_user_preferences(runtime: ToolRuntime) -> str:
    """Get all saved preferences for the current user. Use when you need to recall the user's name or preferences."""
    prefs = runtime.store.get(("user_prefs",), runtime.context.user_id)
    if prefs and prefs.value:
        return str(prefs.value)
    return "No preferences saved yet."


def init_model():
    """Initialize the chat model."""
    return init_chat_model("openai:gpt-4o", temperature=0.3)


def build_agent(model):
    """Build the customer service agent with memory."""
    checkpointer = InMemorySaver()
    store = InMemoryStore()

    agent = create_agent(
        model=model,
        tools=[remember_preference, get_user_preferences],
        system_prompt=(
            "You are a helpful customer service bot. "
            "You remember user details (like their name and preferences) across the conversation. "
            "When the user tells you their name or a preference, use the remember_preference tool to save it. "
            "When you need to recall their details, use the get_user_preferences tool. "
            "Always address the user by their name if you know it."
        ),
        checkpointer=checkpointer,
        store=store,
    )
    return agent


def main():
    model = init_model()
    agent = build_agent(model)

    # Create a unique thread for this conversation
    config = {"configurable": {"thread_id": str(uuid7())}}

    # First interaction: user provides their name
    result1 = agent.invoke(
        {"messages": [{"role": "user", "content": "Hi! My name is Alice."}]},
        config=config,
    )
    print("Bot:", result1["messages"][-1].content)
    print("---")

    # Second interaction: user provides a preference
    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "I prefer concise answers."}]},
        config=config,
    )
    print("Bot:", result2["messages"][-1].content)
    print("---")

    # Third interaction: test if the bot remembers
    result3 = agent.invoke(
        {"messages": [{"role": "user", "content": "What's my name and what do I prefer?"}]},
        config=config,
    )
    print("Bot:", result3["messages"][-1].content)


if __name__ == "__main__":
    main()