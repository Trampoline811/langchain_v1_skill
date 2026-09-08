import os
from typing import Literal, Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain.tools import ToolRuntime

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@tool
def write_code(requirement: str, language: str = "python") -> str:
    """Write production-quality code based on a requirement description.

    Args:
        requirement: Detailed functional requirement for the code.
        language: Target programming language (default: python).
    """
    # In a real system, this would call an LLM or code generation service.
    return (
        f"# Generated {language} code for: {requirement}\n"
        f"def implemented_feature():\n"
        f"    # TODO: implement {requirement}\n"
        f"    pass\n"
    )


@tool
def review_code(code: str, focus: Literal["bugs", "style", "security"] = "bugs") -> str:
    """Review provided code and return a list of issues found.

    Args:
        code: The source code to review.
        focus: Review focus area (bugs, style, or security).
    """
    # In a real system, this would call an LLM-based code reviewer.
    issues = []
    if "TODO" in code:
        issues.append("Found TODO placeholder — implementation incomplete.")
    if "pass" in code and focus == "bugs":
        issues.append("Found bare 'pass' statement — likely missing logic.")
    if not issues:
        issues.append(f"No obvious {focus} issues detected.")
    return "\n".join(f"- {issue}" for issue in issues)


# ---------------------------------------------------------------------------
# Model initialization (isolated in its own function)
# ---------------------------------------------------------------------------
def init_model(model_name: Optional[str] = None) -> object:
    """Initialize and return a chat model instance.

    Args:
        model_name: Optional model identifier (e.g., "openai:gpt-4o").
                    Defaults to environment variable MODEL_NAME or a sensible default.
    """
    model_id = model_name or os.getenv("MODEL_NAME", "openai:gpt-4o")
    return init_chat_model(model_id)


# ---------------------------------------------------------------------------
# Agent construction (isolated in its own function)
# ---------------------------------------------------------------------------
def build_manager_agent(model: object):
    """Build the Manager agent that routes tasks to Coder or Reviewer sub-agents.

    The Manager uses two sub-agents (Coder and Reviewer) as tools.
    """
    # --- Sub-agent: Coder ---
    coder_agent = create_agent(
        model=model,
        tools=[write_code],
        system_prompt=(
            "You are a senior software engineer. "
            "Given a requirement, write clean, correct, and efficient code. "
            "Use the write_code tool to produce the final code."
        ),
        name="coder",
    )

    # --- Sub-agent: Reviewer ---
    reviewer_agent = create_agent(
        model=model,
        tools=[review_code],
        system_prompt=(
            "You are a meticulous code reviewer. "
            "Given a piece of code, analyze it for bugs, style issues, and security "
            "vulnerabilities. Use the review_code tool to report findings."
        ),
        name="reviewer",
    )

    # --- Tool wrappers for the sub-agents ---
    @tool
    def delegate_to_coder(requirement: str, runtime: ToolRuntime) -> Command:
        """Delegate a coding task to the Coder sub-agent.

        Args:
            requirement: The coding requirement to implement.
        """
        result = coder_agent.invoke(
            {"messages": [{"role": "user", "content": requirement}]}
        )
        final_answer = result["messages"][-1].content
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Coder result: {final_answer}",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    @tool
    def delegate_to_reviewer(code: str, runtime: ToolRuntime) -> Command:
        """Delegate a code review task to the Reviewer sub-agent.

        Args:
            code: The code to review.
        """
        result = reviewer_agent.invoke(
            {"messages": [{"role": "user", "content": f"Review this code:\n{code}"}]}
        )
        final_answer = result["messages"][-1].content
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Reviewer result: {final_answer}",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    # --- Manager agent ---
    manager_agent = create_agent(
        model=model,
        tools=[delegate_to_coder, delegate_to_reviewer],
        system_prompt=(
            "You are an engineering manager. You receive a task and decide whether it "
            "should be handled by the Coder (implementation) or the Reviewer (code review). "
            "If the task asks to write or implement code, delegate to the Coder. "
            "If the task asks to review or analyze existing code, delegate to the Reviewer. "
            "Always delegate — never try to solve the task yourself."
        ),
        name="manager",
    )

    return manager_agent


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 1. Initialize the model (inside the main block, not at module level)
    model = init_model()

    # 2. Build the manager agent
    manager = build_manager_agent(model)

    # 3. Example usage: route a coding task
    coding_task = (
        "Write a Python function that calculates the Fibonacci sequence up to n terms."
    )
    print("=== Delegating coding task to Manager ===")
    coding_response = manager.invoke(
        {"messages": [{"role": "user", "content": coding_task}]}
    )
    print("Manager final message:", coding_response["messages"][-1].content)

    print("\n=== Delegating review task to Manager ===")
    code_sample = """
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
"""
    review_task = f"Review the following code for bugs and performance issues:\n{code_sample}"
    review_response = manager.invoke(
        {"messages": [{"role": "user", "content": review_task}]}
    )
    print("Manager final message:", review_response["messages"][-1].content)