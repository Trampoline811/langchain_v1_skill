from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.agents.middleware import HumanInTheLoopMiddleware, ToolRetryMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.utils.uuid import uuid7


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    # Simulate sending email
    return f"Email sent to {to} with subject '{subject}'"


def init_model():
    """Initialize the chat model."""
    return init_chat_model("openai:gpt-5.5", temperature=0)


def build_agent(model):
    """Build the agent with HITL and retry middleware."""
    checkpointer = InMemorySaver()

    agent = create_agent(
        model=model,
        tools=[send_email],
        system_prompt="You are a helpful assistant that can send emails.",
        checkpointer=checkpointer,
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "send_email": {"allowed_decisions": ["approve", "reject"]}
                }
            ),
            ToolRetryMiddleware(max_retries=3),
        ],
    )
    return agent, checkpointer


if __name__ == "__main__":
    model = init_model()
    agent, checkpointer = build_agent(model)

    config = {"configurable": {"thread_id": str(uuid7())}}

    # First invocation triggers HITL interrupt
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Please send an email to john@example.com with subject 'Hello' and body 'Hi John!'",
                }
            ]
        },
        config=config,
    )

    if result.interrupts:
        print("Interrupted! Waiting for human approval...")
        # Simulate human approving the action
        result = agent.invoke(
            Command(resume={"type": "approve"}),
            config=config,
        )
        print("Email approved and sent.")
    else:
        print("No interrupt triggered.")

    print(result["messages"][-1].content)