import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage


# ---------- 数据模型 ----------
class CandidateInfo(BaseModel):
    """候选人结构化信息"""
    name: str = Field(description="候选人姓名")
    skills: List[str] = Field(description="候选人技能列表")
    score: float = Field(description="候选人综合评分（0-100）")


# ---------- 工具 ----------
@tool
def extract_skills(text: str) -> str:
    """从简历文本中提取技能关键词，返回逗号分隔的技能列表"""
    # 简单关键词匹配示例（实际可替换为更智能的提取）
    skill_keywords = [
        "python", "java", "c++", "sql", "机器学习", "深度学习", "tensorflow",
        "pytorch", "docker", "kubernetes", "aws", "azure", "gcp", "react",
        "vue", "node.js", "flask", "django", "pandas", "numpy", "scikit-learn"
    ]
    found = []
    lower_text = text.lower()
    for skill in skill_keywords:
        if skill.lower() in lower_text:
            found.append(skill)
    return ", ".join(found) if found else "未发现明确技能"


@tool
def calculate_score(text: str) -> str:
    """根据简历文本长度和关键词密度计算一个基础评分（0-100）"""
    # 简单启发式评分：长度 + 技能数量
    skill_tool = extract_skills
    skills_str = skill_tool.invoke({"text": text})
    skills_count = len([s for s in skills_str.split(",") if s.strip()])
    length_score = min(len(text) / 100, 50)  # 长度最多50分
    skill_score = min(skills_count * 10, 50)  # 每个技能10分，最多50分
    total = length_score + skill_score
    return str(round(total, 1))


# ---------- 模型初始化 ----------
def init_model() -> ChatOpenAI:
    """初始化LLM模型（使用OpenAI兼容接口）"""
    # 请设置环境变量 OPENAI_API_KEY 或在此处直接传入
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key,
        base_url=base_url,
    )


# ---------- Agent 构建 ----------
def build_agent(llm: ChatOpenAI) -> AgentExecutor:
    """构建简历解析Agent"""
    # 工具列表
    tools = [extract_skills, calculate_score]
    
    # 系统提示词
    system_prompt = """你是一个专业的简历解析助手。你的任务是从用户提供的简历文本中提取结构化信息。
请严格按照以下步骤操作：
1. 首先使用 extract_skills 工具提取技能列表
2. 然后使用 calculate_score 工具计算候选人评分
3. 最后综合所有信息，输出完整的候选人信息

注意：必须使用工具获取信息，不要凭空编造。"""
    
    # 创建Agent
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
    )
    
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )


# ---------- 主处理函数 ----------
def parse_resume(agent: AgentExecutor, resume_text: str) -> CandidateInfo:
    """执行简历解析"""
    # 使用Pydantic解析器确保输出格式
    parser = PydanticOutputParser(pydantic_object=CandidateInfo)
    
    # 构建最终输出提示
    output_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个数据格式化助手。根据Agent的分析结果，生成严格的JSON输出。\n{format_instructions}"),
        ("human", "Agent分析结果：{agent_output}\n请提取候选人姓名、技能列表和评分。"),
    ])
    
    # 运行Agent获取原始分析
    result = agent.invoke({"input": f"请解析以下简历：\n{resume_text}"})
    agent_output = result["output"]
    
    # 使用LLM进行最终格式化
    llm = init_model()
    chain = output_prompt | llm | parser
    formatted = chain.invoke({
        "format_instructions": parser.get_format_instructions(),
        "agent_output": agent_output
    })
    
    return formatted


# ---------- 主入口 ----------
if __name__ == "__main__":
    # 示例简历文本
    sample_resume = """
    张三
    联系方式：zhangsan@email.com | 138-0000-0000
    
    教育背景：
    北京大学 计算机科学 硕士 (2020-2023)
    
    工作经历：
    2023-至今 ABC科技 高级后端工程师
    - 使用Python和Django开发微服务架构
    - 负责机器学习模型部署，使用TensorFlow和PyTorch
    
    2021-2023 XYZ公司 后端开发实习生
    - 使用Java和Spring Boot开发RESTful API
    - 参与SQL数据库优化
    
    技能：
    Python, Java, SQL, TensorFlow, PyTorch, Docker, Kubernetes, AWS
    
    项目经验：
    1. 智能推荐系统 - 使用深度学习技术实现用户行为预测
    2. 容器化部署平台 - 使用Docker和K8s实现自动化部署
    
    证书：
    AWS认证解决方案架构师
    """
    
    print("=== 简历解析Agent示例 ===")
    print("正在初始化模型...")
    model = init_model()
    
    print("正在构建Agent...")
    agent = build_agent(model)
    
    print("正在解析简历...")
    try:
        candidate = parse_resume(agent, sample_resume)
        print("\n=== 解析结果 ===")
        print(f"姓名: {candidate.name}")
        print(f"技能: {', '.join(candidate.skills)}")
        print(f"评分: {candidate.score}")
        print("\n完整JSON输出:")
        print(candidate.model_dump_json(indent=2))
    except Exception as e:
        print(f"解析失败: {e}")
        print("提示：请确保已设置OPENAI_API_KEY环境变量")