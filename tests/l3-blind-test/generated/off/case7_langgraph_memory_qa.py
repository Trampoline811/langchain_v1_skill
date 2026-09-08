from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os


class State(TypedDict):
    messages: Annotated[list, add_messages]
    turns: int


def initialize_model():
    """Initialize the chat model."""
    api_key = os.getenv("OPENAI_API_KEY", "sk-dummy")
    model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
    return model


def build_graph(model):
    """Build the LangGraph state graph with persistence."""
    graph = StateGraph(State)

    def assistant(state: State) -> dict:
        """Generate a response and append to messages."""
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    def bump(state: State) -> dict:
        """Increment the turn counter."""
        return {"turns": state["turns"] + 1}

    graph.add_node("assistant", assistant)
    graph.add_node("bump", bump)

    graph.add_edge(START, "assistant")
    graph.add_edge("assistant", "bump")
    graph.add_edge("bump", END)

    checkpointer = InMemorySaver()
    return graph.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    model = initialize_model()
    app = build_graph(model)

    config = {"configurable": {"thread_id": "test-thread"}}

    # First invocation
    result1 = app.invoke(
        {"messages": [HumanMessage(content="Hi, my name is Alice.")], "turns": 0},
        config,
    )
    print("Turn 1 - Assistant:", result1["messages"][-1].content)
    print("Turn 1 - Turns:", result1["turns"])

    # Second invocation (should remember context)
    result2 = app.invoke(
        {"messages": [HumanMessage(content="What's my name?")], "turns": result1["turns"]},
        config,
    )
    print("Turn 2 - Assistant:", result2["messages"][-1].content)
    print("Turn 2 - Turns:", result2["turns"])