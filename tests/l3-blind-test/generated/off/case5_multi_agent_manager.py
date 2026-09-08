import json
from typing import Dict, List, Optional, Any

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI


# ---------- 工具定义 ----------
class CodeTaskInput(BaseModel):
    task_description: str = Field(description="任务描述，例如：实现一个函数计算斐波那契数列")
    language: str = Field(default="python", description="编程语言")


class ReviewTaskInput(BaseModel):
    code: str = Field(description="需要审查的代码")
    review_focus: str = Field(default="bug, 性能, 可读性", description="审查重点")


@tool("code_writer", args_schema=CodeTaskInput)
def code_writer(task_description: str, language: str = "python") -> str:
    """根据任务描述生成代码（模拟 Coder Agent 行为）"""
    # 实际场景中这里会调用 LLM 生成代码，此处用简单模板模拟
    return f"# 由 Coder Agent 生成的 {language} 代码\n# 任务: {task_description}\ndef solution():\n    pass  # TODO: 实现具体逻辑"


@tool("code_reviewer", args_schema=ReviewTaskInput)
def code_reviewer(code: str, review_focus: str = "bug, 性能, 可读性") -> str:
    """对代码进行审查并返回审查意见（模拟 Reviewer Agent 行为）"""
    # 实际场景中这里会调用 LLM 进行代码审查，此处用简单模板模拟
    return f"# 由 Reviewer Agent 给出的审查意见\n# 审查重点: {review_focus}\n# 代码长度: {len(code)} 字符\n# 建议: 1. 检查边界条件 2. 优化时间复杂度"


# ---------- 模型初始化 ----------
def init_llm() -> ChatOpenAI:
    """初始化 LLM 模型"""
    # 请替换为你的 API key 和 base_url
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key="your-api-key",  # 或从环境变量读取
        base_url="https://api.openai.com/v1",  # 或使用代理
    )


# ---------- Agent 构建 ----------
def build_coder_agent(llm: ChatOpenAI) -> AgentExecutor:
    """构建 Coder 子 Agent"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的代码编写 Agent。根据用户需求生成高质量代码。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    tools = [code_writer]
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


def build_reviewer_agent(llm: ChatOpenAI) -> AgentExecutor:
    """构建 Reviewer 子 Agent"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的代码审查 Agent。对代码进行深入分析，找出潜在问题。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    tools = [code_reviewer]
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


def build_manager_agent(llm: ChatOpenAI, coder_agent: AgentExecutor, reviewer_agent: AgentExecutor) -> AgentExecutor:
    """构建 Manager Agent，负责任务分发"""
    
    # 定义 Manager 的工具：调用子 Agent
    class CoderCallInput(BaseModel):
        task: str = Field(description="需要 Coder 完成的任务描述")
    
    class ReviewerCallInput(BaseModel):
        code: str = Field(description="需要 Reviewer 审查的代码")
    
    @tool("call_coder", args_schema=CoderCallInput)
    def call_coder(task: str) -> str:
        """将编码任务分发给 Coder Agent"""
        result = coder_agent.invoke({"input": task})
        return result["output"]
    
    @tool("call_reviewer", args_schema=ReviewerCallInput)
    def call_reviewer(code: str) -> str:
        """将代码审查任务分发给 Reviewer Agent"""
        result = reviewer_agent.invoke({"input": f"请审查以下代码:\n{code}"})
        return result["output"]
    
    manager_tools = [call_coder, call_reviewer]
    
    manager_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个研发团队的 Manager Agent。你的职责是：
1. 分析用户请求
2. 如果是编码任务（如实现功能、写代码），调用 call_coder 工具
3. 如果是代码审查任务（如 review、检查代码），调用 call_reviewer 工具
4. 如果任务包含多个步骤，可以依次调用多个工具
5. 最后汇总结果返回给用户

请根据任务类型智能选择工具。"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    manager_agent = create_openai_tools_agent(llm, manager_tools, manager_prompt)
    return AgentExecutor(agent=manager_agent, tools=manager_tools, verbose=True, handle_parsing_errors=True)


# ---------- 主流程 ----------
def main():
    # 1. 初始化模型
    llm = init_llm()
    
    # 2. 构建子 Agent
    coder_agent = build_coder_agent(llm)
    reviewer_agent = build_reviewer_agent(llm)
    
    # 3. 构建 Manager Agent
    manager_agent = build_manager_agent(llm, coder_agent, reviewer_agent)
    
    # 4. 测试示例
    print("=" * 50)
    print("测试1: 编码任务")
    print("=" * 50)
    result1 = manager_agent.invoke({
        "input": "请帮我写一个 Python 函数，计算两个数的最大公约数"
    })
    print(f"Manager 回复: {result1['output']}")
    
    print("\n" + "=" * 50)
    print("测试2: 代码审查任务")
    print("=" * 50)
    sample_code = """
def add(a, b):
    return a + b

def divide(a, b):
    return a / b  # 潜在除零错误
"""
    result2 = manager_agent.invoke({
        "input": f"请审查以下代码，找出潜在问题:\n{sample_code}"
    })
    print(f"Manager 回复: {result2['output']}")
    
    print("\n" + "=" * 50)
    print("测试3: 混合任务（先写代码再审查）")
    print("=" * 50)
    result3 = manager_agent.invoke({
        "input": "请写一个二分查找算法，然后审查你写的代码"
    })
    print(f"Manager 回复: {result3['output']}")


if __name__ == "__main__":
    main()