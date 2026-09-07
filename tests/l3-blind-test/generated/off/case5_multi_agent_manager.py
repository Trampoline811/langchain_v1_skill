import json
from typing import Dict, List, Optional, Any

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# ---------- 模型初始化 ----------
def init_llm(model_name: str = "gpt-4o-mini", temperature: float = 0.1) -> ChatOpenAI:
    """初始化 LLM 模型"""
    return ChatOpenAI(model=model_name, temperature=temperature)


# ---------- 子 Agent 工具 ----------
class CodeTask(BaseModel):
    task_description: str = Field(description="任务描述")
    code_context: Optional[str] = Field(default="", description="相关代码上下文")


class ReviewTask(BaseModel):
    code: str = Field(description="需要审查的代码")
    review_focus: Optional[str] = Field(default="bug, 安全性, 性能", description="审查重点")


@tool("code_writer", args_schema=CodeTask)
def code_writer(task_description: str, code_context: str = "") -> str:
    """根据任务描述编写代码。"""
    # 实际场景中这里会调用 LLM 生成代码，此处简化为返回模拟结果
    return f"已生成代码: 实现 {task_description} 的代码 (基于上下文: {code_context[:50]}...)"


@tool("code_reviewer", args_schema=ReviewTask)
def code_reviewer(code: str, review_focus: str = "bug, 安全性, 性能") -> str:
    """审查代码并返回审查意见。"""
    # 实际场景中这里会调用 LLM 审查代码，此处简化为返回模拟结果
    return f"审查意见: 代码 {code[:50]}... 在 {review_focus} 方面未发现明显问题"


# ---------- Agent 构建 ----------
def build_coder_agent(llm: ChatOpenAI) -> AgentExecutor:
    """构建 Coder Agent"""
    tools = [code_writer]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的代码编写工程师。根据任务描述编写高质量代码。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


def build_reviewer_agent(llm: ChatOpenAI) -> AgentExecutor:
    """构建 Reviewer Agent"""
    tools = [code_reviewer]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个资深代码审查专家。仔细审查代码并给出专业意见。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


def build_manager_agent(llm: ChatOpenAI, coder_agent: AgentExecutor, reviewer_agent: AgentExecutor) -> AgentExecutor:
    """构建 Manager Agent，负责任务分发"""
    
    @tool("dispatch_to_coder", args_schema=CodeTask)
    def dispatch_to_coder(task_description: str, code_context: str = "") -> str:
        """将编码任务分发给 Coder Agent"""
        result = coder_agent.invoke({
            "input": f"请完成以下编码任务: {task_description}\n上下文: {code_context}",
            "chat_history": []
        })
        return result["output"]
    
    @tool("dispatch_to_reviewer", args_schema=ReviewTask)
    def dispatch_to_reviewer(code: str, review_focus: str = "bug, 安全性, 性能") -> str:
        """将代码审查任务分发给 Reviewer Agent"""
        result = reviewer_agent.invoke({
            "input": f"请审查以下代码:\n{code}\n审查重点: {review_focus}",
            "chat_history": []
        })
        return result["output"]
    
    tools = [dispatch_to_coder, dispatch_to_reviewer]
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个研发团队的管理者。你的职责是：
1. 分析任务类型
2. 如果是编码任务，使用 dispatch_to_coder 工具分发给 Coder
3. 如果是代码审查任务，使用 dispatch_to_reviewer 工具分发给 Reviewer
4. 如果是复杂任务，可以拆解后分别分发
请根据任务内容智能判断并分发。"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


# ---------- 主流程 ----------
def run_team_agent():
    """运行整个 Agent 团队系统"""
    # 初始化模型
    llm = init_llm()
    
    # 构建子 Agent
    coder_agent = build_coder_agent(llm)
    reviewer_agent = build_reviewer_agent(llm)
    
    # 构建 Manager Agent
    manager_agent = build_manager_agent(llm, coder_agent, reviewer_agent)
    
    # 测试任务
    test_tasks = [
        "请编写一个 Python 函数，用于计算斐波那契数列的第 n 项",
        "请审查以下代码: def add(a,b): return a+b  # 简单加法函数",
        "请实现一个用户登录功能，包含密码加密和验证",
    ]
    
    print("=" * 60)
    print("研发团队 Agent 系统启动")
    print("=" * 60)
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n--- 任务 {i}: {task[:50]}... ---")
        try:
            response = manager_agent.invoke({
                "input": task,
                "chat_history": []
            })
            print(f"任务 {i} 完成，结果: {response['output'][:200]}...")
        except Exception as e:
            print(f"任务 {i} 执行失败: {e}")
    
    print("\n" + "=" * 60)
    print("所有任务执行完毕")
    print("=" * 60)


if __name__ == "__main__":
    run_team_agent()