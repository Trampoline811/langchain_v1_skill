import os
from typing import Dict, Any, Optional

from langchain.memory import ConversationSummaryBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# ---------------------------
# 模型初始化（独立函数）
# ---------------------------
def init_llm() -> ChatOpenAI:
    """初始化大语言模型（使用 OpenAI 兼容接口）"""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )

# ---------------------------
# 工具定义（用于记忆用户信息）
# ---------------------------
@tool
def remember_user_info(name: Optional[str] = None, preference: Optional[str] = None) -> str:
    """记住用户提供的姓名或偏好信息。调用时传入 name 或 preference 参数。"""
    # 实际项目中可存储到数据库，这里通过全局变量模拟
    global user_memory_store
    if name:
        user_memory_store["name"] = name
    if preference:
        user_memory_store["preference"] = preference
    return f"已记住：姓名={user_memory_store.get('name')}, 偏好={user_memory_store.get('preference')}"

@tool
def get_user_info() -> str:
    """获取当前已记住的用户信息（姓名和偏好）"""
    global user_memory_store
    return f"当前用户信息：姓名={user_memory_store.get('name', '未知')}, 偏好={user_memory_store.get('preference', '未知')}"

# 全局存储（模拟数据库）
user_memory_store: Dict[str, str] = {}

# ---------------------------
# Agent 构建（独立函数）
# ---------------------------
def build_agent(llm: ChatOpenAI) -> AgentExecutor:
    """构建带记忆的客服 Agent"""
    
    # 系统提示词，强调使用记忆
    system_prompt = """你是一个贴心的客服助手。你可以通过工具记住用户的姓名和偏好，并在对话中主动使用这些信息。
    当用户提到自己的姓名或偏好时，请调用 remember_user_info 工具保存。
    当需要了解用户信息时，可以调用 get_user_info 工具。
    在回复中，如果知道用户姓名，请称呼其姓名；如果知道偏好，请根据偏好提供个性化建议。"""
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 工具列表
    tools = [remember_user_info, get_user_info]

    # 创建 Agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 使用带记忆的 Agent Executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
    )

    return agent_executor

# ---------------------------
# 带会话历史的执行器
# ---------------------------
def create_chat_agent() -> RunnableWithMessageHistory:
    """创建带会话历史的聊天 Agent"""
    llm = init_llm()
    agent_executor = build_agent(llm)
    
    # 使用内存存储会话历史
    store: Dict[str, ChatMessageHistory] = {}
    
    def get_session_history(session_id: str) -> ChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]
    
    # 包装为带历史记录的 Runnable
    with_message_history = RunnableWithMessageHistory(
        agent_executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    
    return with_message_history

# ---------------------------
# 主程序入口
# ---------------------------
if __name__ == "__main__":
    # 初始化聊天 Agent
    chat_agent = create_chat_agent()
    
    # 模拟对话（使用固定 session_id）
    session_id = "customer-001"
    
    print("=== 客服 Bot 启动（输入 'exit' 退出）===")
    print("提示：你可以告诉 Bot 你的姓名和偏好，例如：'我叫张三，喜欢简洁的回答'")
    
    while True:
        user_input = input("\n你: ")
        if user_input.lower() == "exit":
            print("客服 Bot: 再见！祝您生活愉快！")
            break
        
        # 调用 Agent
        response = chat_agent.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}},
        )
        
        print(f"客服 Bot: {response['output']}")
        
        # 显示当前记忆状态（调试用）
        print(f"\n[记忆状态] {user_memory_store}")