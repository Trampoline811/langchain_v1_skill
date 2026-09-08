import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None


class State(TypedDict):
    messages: Annotated[list, operator.add]
    turns: int


def _get_model():
    """Initialize the chat model inside a function (never at module level)."""
    if ChatAnthropic is not None:
        return ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    if ChatOpenAI is not None:
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    raise RuntimeError(
        "No chat model provider installed. Install 'langchain-anthropic' "
        "or 'langchain-openai'."
    )


def assistant(state: State) -> dict:
    """Generate a reply and append it to messages."""
    model = _get_model()
    response = model.invoke(state["messages"])
    return {"messages": [response]}


def bump(state: State) -> dict:
    """Increment the turn counter."""
    return {"turns": state["turns"] + 1}


def build_graph():
    """Build and compile the StateGraph with an in-memory checkpointer."""
    builder = StateGraph(State)
    builder.add_node("assistant", assistant)
    builder.add_node("bump", bump)

    builder.add_edge(START, "assistant")
    builder.add_edge("assistant", "bump")
    builder.add_edge("bump", END)

    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    graph = build_graph()

    config = {"configurable": {"thread_id": "thread-1"}}

    first = graph.invoke(
        {"messages": [{"role": "user", "content": "Hi, my name is Alice."}], "turns": 0},
        config,
    )
    print("First reply:", first["messages"][-1].content)
    print("Turns after first call:", first["turns"])

    second = graph.invoke(
        {"messages": [{"role": "user", "content": "What is my name?"}], "turns": first["turns"]},
        config,
    )
    print("Second reply:", second["messages"][-1].content)
    print("Turns after second call:", second["turns"])