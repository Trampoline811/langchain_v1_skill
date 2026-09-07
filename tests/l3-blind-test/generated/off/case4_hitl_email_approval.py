import json
from typing import Any, Callable, Dict, List, Optional, Union

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# ========== 工具定义 ==========

class SendEmailInput(BaseModel):
    recipient: str = Field(description="收件人邮箱地址")
    subject: str = Field(description="邮件主题")
    body: str = Field(description="邮件正文")

@tool("send_email", args_schema=SendEmailInput)
def send_email(recipient: str, subject: str, body: str) -> str:
    """发送一封邮件（需要人工审批）"""
    # 模拟邮件发送，可能失败
    import random
    if random.random() < 0.3:
        raise ConnectionError("邮件服务器连接失败")
    return f"邮件已发送至 {recipient}，主题：{subject}"

# ========== 审批回调 ==========

class ApprovalCallbackHandler(BaseCallbackHandler):
    """在工具调用前进行人工审批，并自动重试失败的工具调用"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.approval_func: Optional[Callable[[Dict[str, Any]], bool]] = None
        self.retry_counts: Dict[str, int] = {}
    
    def set_approval_func(self, func: Callable[[Dict[str, Any]], bool]):
        """设置审批函数，接收工具调用信息，返回是否批准"""
        self.approval_func = func
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """工具开始前调用，用于审批"""
        tool_name = serialized.get("name", "unknown_tool")
        if tool_name == "send_email" and self.approval_func:
            # 解析输入
            try:
                tool_input = json.loads(input_str) if input_str else {}
            except:
                tool_input = {}
            
            approval_info = {
                "tool": tool_name,
                "input": tool_input,
                "run_id": str(run_id) if run_id else None
            }
            
            if not self.approval_func(approval_info):
                raise PermissionError(f"用户拒绝了 {tool_name} 工具调用")
    
    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """工具出错时调用，用于自动重试"""
        run_id_str = str(run_id) if run_id else "unknown"
        current_retries = self.retry_counts.get(run_id_str, 0)
        
        if current_retries < self.max_retries:
            self.retry_counts[run_id_str] = current_retries + 1
            # 这里不能直接重试，需要抛出特殊异常让 Agent 重试
            # 实际上 LangChain 的 AgentExecutor 会处理重试逻辑
            # 我们通过修改错误信息来提示重试
            error.args = (f"{error.args[0]} (自动重试 {current_retries + 1}/{self.max_retries})",)
        else:
            self.retry_counts.pop(run_id_str, None)

# ========== 模型初始化 ==========

def init_model() -> ChatOpenAI:
    """初始化语言模型"""
    # 注意：实际使用时需要设置 OPENAI_API_KEY 环境变量
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        max_retries=2,  # 模型自身的重试
    )

# ========== Agent 构建 ==========

def build_agent(
    model: ChatOpenAI,
    tools: List[BaseTool],
    approval_callback: ApprovalCallbackHandler
) -> AgentExecutor:
    """构建带审批和重试机制的 Agent"""
    
    # 创建带审批的 Agent
    prompt = SystemMessage(content=(
        "你是一个智能助手，可以调用工具完成任务。"
        "当需要发送邮件时，必须使用 send_email 工具。"
        "如果工具调用失败，请重试。"
    ))
    
    # 使用标准方式创建 agent
    from langchain.agents import create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "你是一个智能助手，可以调用工具完成任务。当需要发送邮件时，必须使用 send_email 工具。如果工具调用失败，请重试。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(model, tools, prompt_template)
    
    # 创建执行器，并添加审批回调
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,  # 防止无限循环
        callbacks=[approval_callback],
    )
    
    return executor

# ========== 审批函数示例 ==========

def default_approval_func(tool_call_info: Dict[str, Any]) -> bool:
    """默认审批函数：打印信息并询问用户"""
    print("\n=== 工具审批请求 ===")
    print(f"工具: {tool_call_info['tool']}")
    print(f"输入: {json.dumps(tool_call_info['input'], ensure_ascii=False, indent=2)}")
    
    response = input("是否批准此调用？(y/n): ").strip().lower()
    return response in ("y", "yes")

# ========== 主程序 ==========

def main():
    """主程序入口"""
    # 1. 初始化模型
    model = init_model()
    
    # 2. 创建审批回调
    approval_callback = ApprovalCallbackHandler(max_retries=3)
    approval_callback.set_approval_func(default_approval_func)
    
    # 3. 构建 Agent
    tools = [send_email]
    agent_executor = build_agent(model, tools, approval_callback)
    
    # 4. 运行示例任务
    print("=== 开始执行任务 ===")
    print("示例：请给 test@example.com 发送一封测试邮件，主题为'测试'，内容为'这是一封测试邮件'")
    
    result = agent_executor.invoke({
        "input": "请给 test@example.com 发送一封测试邮件，主题为'测试'，内容为'这是一封测试邮件'"
    })
    
    print("\n=== 执行结果 ===")
    print(result["output"])

if __name__ == "__main__":
    main()