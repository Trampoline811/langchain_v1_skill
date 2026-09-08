from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ToolRetryMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.utils.uuid import uuid7


@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email to a recipient. Use when the user asks to send an email."""
    # Simulate sending an email
    return f"Email sent to {recipient} with subject '{subject}'"


@tool
def unreliable_tool(query: str) -> str:
    """A tool that sometimes fails. Use for testing retries."""
    import random

    if random.random() < 0.7:
        raise ValueError("Simulated transient failure")
    return f"Successfully processed: {query}"


def init_model():
    """Initialize the chat model."""
    return init_chat_model("openai:gpt-4o", temperature=0)


def build_agent():
    """Build the agent with HITL and retry middleware."""
    model = init_model()

    agent = create_agent(
        model=model,
        tools=[send_email, unreliable_tool],
        system_prompt="You are a helpful assistant. Use tools when appropriate.",
        checkpointer=InMemorySaver(),  # Required for HITL
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "send_email": {"allowed_decisions": ["approve", "reject"]}
                }
            ),
            ToolRetryMiddleware(max_retries=3, backoff_factor=2.0),
        ],
    )
    return agent


if __name__ == "__main__":
    agent = build_agent()
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

    # Test 1: Email with HITL approval
    print("=== Test 1: Email with HITL approval ===")
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Send an email to john@example.com with subject 'Hello' and body 'Hi John, this is a test.'",
                }
            ]
        },
        config=config,
    )

    # Check if interrupted
    if result.get("interrupts"):
        print("Agent interrupted for approval.")
        print(f"Interrupt info: {result['interrupts'][0]}")
        # Approve the email
        result = agent.invoke(
            Command(resume={"type": "approve"}),
            config=config,
        )
        print(f"Final response: {result['messages'][-1].content}")
    else:
        print(f"Response: {result['messages'][-1].content}")

    # Test 2: Unreliable tool with retry
    print("\n=== Test 2: Unreliable tool with retry ===")
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Process the query 'test data' using the unreliable tool.",
                }
            ]
        },
        config={"configurable": {"thread_id": str(uuid7())}},
    )
    print(f"Final response: {result['messages'][-1].content}")