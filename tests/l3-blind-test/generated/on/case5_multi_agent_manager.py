import uuid
from typing import Literal

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.utils.uuid import uuid7


# ---------- 工具定义 ----------
@tool
def write_code(task: str) -> str:
    """根据任务描述编写 Python 代码。"""
    return f"def solution():\n    # TODO: {task}\n    return 'implemented'"


@tool
def review_code(code: str) -> str:
    """审查给定的代码并返回改进建议。"""
    return f"Reviewed code: {code[:50]}... Looks good, but consider adding type hints."


# ---------- 模型初始化 ----------
def init_models():
    """初始化 Manager、Coder、Reviewer 三个模型。"""
    manager_model = init_chat_model("openai:gpt-4o", temperature=0.1)
    coder_model = init_chat_model("openai:gpt-4o", temperature=0.3)
    reviewer_model = init_chat_model("openai:gpt-4o", temperature=0.2)
    return manager_model, coder_model, reviewer_model


# ---------- Agent 构建 ----------
def build_agents(manager_model, coder_model, reviewer_model):
    """构建 Manager、Coder、Reviewer 三个 Agent。"""
    # Coder Agent
    coder_agent = create_agent(
        model=coder_model,
        tools=[write_code],
        system_prompt="You are a senior software engineer. Write clean, efficient code.",
        name="coder",
    )

    # Reviewer Agent
    reviewer_agent = create_agent(
        model=reviewer_model,
        tools=[review_code],
        system_prompt="You are a meticulous code reviewer. Provide constructive feedback.",
        name="reviewer",
    )

    # Manager Agent (with sub-agent handoff)
    manager_agent = create_agent(
        model=manager_model,
        tools=[write_code, review_code],
        system_prompt=(
            "You are a tech lead. Decide whether a task needs coding or review. "
            "If it's a new feature, delegate to 'coder'. If it's a code review, delegate to 'reviewer'."
        ),
        name="manager",
        checkpointer=InMemorySaver(),
    )

    return manager_agent, coder_agent, reviewer_agent


# ---------- 主流程 ----------
def run_team(manager_agent, coder_agent, reviewer_agent, task: str):
    """模拟 Manager 分发任务给 Coder 或 Reviewer。"""
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

    # Manager 决定任务类型
    decision = manager_agent.invoke(
        {"messages": [{"role": "user", "content": f"Task: {task}. Should this go to coder or reviewer?"}]},
        config=config,
    )
    last_msg = decision["messages"][-1].content
    print(f"[Manager] {last_msg}")

    # 简单路由逻辑（实际可用 LangGraph 条件边）
    if "review" in task.lower():
        result = reviewer_agent.invoke(
            {"messages": [{"role": "user", "content": f"Review this code: {task}"}]},
            config={"configurable": {"thread_id": str(uuid7())}},
        )
        print(f"[Reviewer] {result['messages'][-1].content}")
    else:
        result = coder_agent.invoke(
            {"messages": [{"role": "user", "content": f"Implement: {task}"}]},
            config={"configurable": {"thread_id": str(uuid7())}},
        )
        print(f"[Coder] {result['messages'][-1].content}")


# ---------- 入口 ----------
if __name__ == "__main__":
    # 初始化
    manager_model, coder_model, reviewer_model = init_models()
    manager_agent, coder_agent, reviewer_agent = build_agents(
        manager_model, coder_model, reviewer_model
    )

    # 测试任务
    run_team(manager_agent, coder_agent, reviewer_agent, "Implement a fibonacci function")
    run_team(manager_agent, coder_agent, reviewer_agent, "Review this code: def foo(): pass")