import os
from typing import Dict, Any, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool

# ---------- 内存与状态管理 ----------
class CustomerMemory:
    """简单的内存存储，用于记录用户姓名和偏好"""
    def __init__(self):
        self.user_data: Dict[str, Dict[str, str]] = {}
    
    def get_user_info(self, user_id: str) -> Dict[str, str]:
        return self.user_data.get(user_id, {})
    
    def update_user_info(self, user_id: str, key: str, value: str):
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id][key] = value

# 全局内存实例（实际生产环境应使用数据库）
customer_memory = CustomerMemory()

# ---------- 工具函数 ----------
@tool
def remember_user_name(user_id: str, name: str) -> str:
    """记住用户的姓名。调用时传入用户ID和姓名。"""
    customer_memory.update_user_info(user_id, "name", name)
    return f"已记住用户 {user_id} 的姓名：{name}"

@tool
def remember_user_preference(user_id: str, preference: str) -> str:
    """记住用户的偏好。调用时传入用户ID和偏好描述。"""
    customer_memory.update_user_info(user_id, "preference", preference)
    return f"已记住用户 {user_id} 的偏好：{preference}"

@tool
def get_user_info(user_id: str) -> str:
    """获取当前用户的所有已知信息（姓名、偏好等）。"""
    info = customer_memory.get_user_info(user_id)
    if not info:
        return "暂无该用户的信息"
    return f"用户信息：姓名={info.get('name', '未知')}, 偏好={info.get('preference', '未知')}"

# ---------- 模型初始化 ----------
def init_llm() -> ChatOpenAI:
    """初始化语言模型"""
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    return ChatOpenAI(
        model="gpt-4",
        temperature=0.7,
        api_key=api_key,
        base_url=os.getenv("OPENAI_API_BASE", None)  # 可选：自定义API地址
    )

# ---------- Agent 构建 ----------
def build_agent(llm: ChatOpenAI, user_id: str) -> AgentExecutor:
    """构建客服 Agent"""
    
    # 创建工具列表
    tools = [
        remember_user_name,
        remember_user_preference,
        get_user_info
    ]
    
    # 创建对话记忆
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        input_key="input",
        output_key="output"
    )
    
    # 创建系统提示词模板
    system_template = """你是一个专业的客服助手。你可以记住用户的姓名和偏好，并在对话中个性化地使用这些信息。

当前用户ID: {user_id}
用户已知信息: {user_info}

你的工作原则：
1. 当用户告诉你他们的姓名时，使用 remember_user_name 工具记住
2. 当用户提到他们的偏好时，使用 remember_user_preference 工具记住
3. 在对话中自然地使用已记住的用户姓名和偏好
4. 如果用户询问你记得什么，使用 get_user_info 工具查看

请始终以友好、专业的语气回复。"""

    system_prompt = PromptTemplate(
        template=system_template,
        input_variables=["user_id", "user_info"]
    )
    
    # 创建 Agent 提示词
    agent_prompt = PromptTemplate.from_template("""你是客服助手。请根据以下信息回答用户问题。

{system_prompt}

对话历史：
{chat_history}

用户输入：{input}

请使用以下工具（如果需要）：
{tools}

工具名称列表：{tool_names}

思考过程：{agent_scratchpad}""")
    
    # 创建 Agent
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=agent_prompt
    )
    
    # 创建 Agent 执行器
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
        early_stopping_method="generate"
    )
    
    # 设置系统提示词（通过额外参数传递）
    user_info = customer_memory.get_user_info(user_id)
    info_str = f"姓名={user_info.get('name', '未知')}, 偏好={user_info.get('preference', '未知')}"
    
    # 将系统信息注入到 memory 中
    memory.chat_memory.add_message(SystemMessage(content=system_prompt.format(
        user_id=user_id,
        user_info=info_str
    )))
    
    return agent_executor

# ---------- 主程序 ----------
def main():
    """主函数：演示客服 Bot 的使用"""
    
    # 模拟用户ID（实际应用中应从会话中获取）
    user_id = "user_12345"
    
    # 初始化模型
    llm = init_llm()
    
    # 构建 Agent
    agent = build_agent(llm, user_id)
    
    print("=" * 50)
    print("客服 Bot 已启动！输入 'exit' 退出")
    print("=" * 50)
    
    # 模拟对话
    test_conversations = [
        "你好，我叫张三",
        "我喜欢喝咖啡，特别是拿铁",
        "你还记得我的名字和喜好是什么吗？",
        "给我推荐一款咖啡吧",
        "我叫李四，请记住我的新名字",
        "我其实更喜欢喝茶",
        "现在你还记得什么？"
    ]
    
    for user_input in test_conversations:
        print(f"\n用户: {user_input}")
        
        if user_input.lower() == 'exit':
            break
        
        try:
            # 获取当前用户信息用于提示
            user_info = customer_memory.get_user_info(user_id)
            info_str = f"姓名={user_info.get('name', '未知')}, 偏好={user_info.get('preference', '未知')}"
            
            # 执行对话
            response = agent.invoke({
                "input": user_input,
                "user_id": user_id,
                "user_info": info_str
            })
            
            print(f"客服: {response['output']}")
            
        except Exception as e:
            print(f"发生错误: {e}")
            print("请检查 API 密钥和网络连接")
            break
    
    print("\n" + "=" * 50)
    print("对话结束。最终用户信息：")
    final_info = customer_memory.get_user_info(user_id)
    print(f"姓名: {final_info.get('name', '未知')}")
    print(f"偏好: {final_info.get('preference', '未知')}")

if __name__ == "__main__":
    main()