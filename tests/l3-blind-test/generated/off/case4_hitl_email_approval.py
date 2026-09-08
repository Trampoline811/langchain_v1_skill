import json
from typing import Any, Dict, List, Optional, Union

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# ---------- 工具定义 ----------
class SendEmailInput(BaseModel):
    recipient: str = Field(description="收件人邮箱地址")
    subject: str = Field(description="邮件主题")
    body: str = Field(description="邮件正文内容")


@tool("send_email", args_schema=SendEmailInput)
def send_email(recipient: str, subject: str, body: str) -> str:
    """发送一封邮件。需要人工审批后才能执行。"""
    # 模拟邮件发送，实际场景中可替换为真实邮件服务
    print(f"\n[邮件已发送] 收件人: {recipient}\n主题: {subject}\n正文: {body}")
    return f"邮件已成功发送至 {recipient}"


# ---------- 人工审批包装器 ----------
class HumanApprovalTool(BaseTool):
    """包装任意工具，在执行前请求人工审批。"""
    name: str = "human_approval_tool"
    description: str = "需要人工审批的工具包装器"
    wrapped_tool: BaseTool = None
    max_retries: int = 3

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """执行工具，带人工审批和自动重试。"""
        for attempt in range(1, self.max_retries + 1):
            # 1. 请求人工审批
            print(f"\n--- 人工审批请求 (尝试 {attempt}/{self.max_retries}) ---")
            print(f"工具: {self.wrapped_tool.name}")
            print(f"参数: {json.dumps(kwargs, ensure_ascii=False, indent=2)}")
            approval = input("是否批准执行此工具调用? (y/n): ").strip().lower()

            if approval not in ("y", "yes"):
                print("❌ 人工拒绝执行工具调用")
                return "工具调用被人工拒绝"

            # 2. 执行工具
            print(f"✅ 人工批准，正在执行工具...")
            try:
                result = self.wrapped_tool.run(*args, **kwargs)
                print(f"工具执行成功: {result}")
                return result
            except Exception as e:
                print(f"⚠️ 工具执行失败 (尝试 {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    print("准备自动重试...")
                else:
                    print("已达到最大重试次数，放弃执行")
                    return f"工具执行失败，已重试 {self.max_retries} 次: {str(e)}"

        return "工具执行失败"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """异步执行工具（简单同步实现）"""
        return self._run(*args, **kwargs)


# ---------- 模型初始化 ----------
def initialize_model() -> ChatOpenAI:
    """初始化语言模型。"""
    # 注意：请设置环境变量 OPENAI_API_KEY，或在此处直接传入
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key="your-api-key-here",  # 替换为实际 API key
    )


# ---------- Agent 构建 ----------
def build_agent(model: ChatOpenAI) -> AgentExecutor:
    """构建带人工审批和自动重试的 Agent。"""
    # 创建带人工审批的邮件工具
    email_tool = HumanApprovalTool(
        wrapped_tool=send_email,
        name="send_email_with_approval",
        description="发送邮件（需要人工审批，失败自动重试最多3次）"
    )

    # 其他普通工具（示例）
    @tool
    def get_current_time() -> str:
        """获取当前时间。"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tools = [email_tool, get_current_time]

    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="你是一个有用的助手。当需要发送邮件时，必须使用 send_email_with_approval 工具。"),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessage(content="{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 创建 Agent
    agent = create_tool_calling_agent(model, tools, prompt)

    # 创建执行器
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )

    return executor


# ---------- 主程序 ----------
if __name__ == "__main__":
    # 初始化模型
    llm = initialize_model()

    # 构建 Agent
    agent_executor = build_agent(llm)

    # 测试对话
    print("=" * 60)
    print("LangChain Agent 演示 - 人工审批 + 自动重试")
    print("=" * 60)

    # 示例1: 发送邮件（需要人工审批）
    print("\n【示例1】请求发送邮件")
    response1 = agent_executor.invoke({
        "input": "请给 test@example.com 发送一封邮件，主题为'测试邮件'，内容为'这是一封测试邮件。'",
        "chat_history": []
    })
    print(f"Agent 回复: {response1['output']}")

    # 示例2: 查询时间（无需审批）
    print("\n【示例2】查询当前时间")
    response2 = agent_executor.invoke({
        "input": "现在几点了？",
        "chat_history": []
    })
    print(f"Agent 回复: {response2['output']}")

    print("\n演示结束。")