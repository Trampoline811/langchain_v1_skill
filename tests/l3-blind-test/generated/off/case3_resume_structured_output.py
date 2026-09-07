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
    score: int = Field(description="候选人综合评分（0-100）")

# ---------- 工具 ----------
@tool
def extract_skills(text: str) -> str:
    """从简历文本中提取技能关键词，返回逗号分隔的技能列表"""
    # 简单关键词匹配示例（实际可用NER或规则）
    skill_keywords = ["Python", "Java", "C++", "SQL", "机器学习", "深度学习", "NLP", "Docker", "Kubernetes", "AWS", "React", "Node.js"]
    found = [skill for skill in skill_keywords if skill.lower() in text.lower()]
    return ", ".join(found) if found else "未发现明确技能"

@tool
def estimate_score(text: str) -> str:
    """根据简历长度和关键词密度估算评分（0-100）"""
    # 简单启发式评分
    score = min(100, len(text) // 10 + text.lower().count("experience") * 2 + text.lower().count("project") * 3)
    return str(score)

# ---------- 模型初始化 ----------
def init_model():
    """初始化LLM模型"""
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key
    )

# ---------- Agent构建 ----------
def build_agent(llm):
    """构建简历解析Agent"""
    # 工具列表
    tools = [extract_skills, estimate_score]
    
    # 提示模板
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="你是一个专业的简历解析助手。请根据提供的简历文本，提取候选人信息并输出结构化JSON。"),
        HumanMessage(content="简历文本：\n{resume_text}\n\n请提取候选人姓名、技能列表和评分。"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    # 创建agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    
    # 定义解析链
    def parse_resume(resume_text: str) -> CandidateInfo:
        # 先调用agent获取中间结果
        result = executor.invoke({"resume_text": resume_text})
        output = result["output"]
        
        # 使用结构化输出解析
        parser = PydanticOutputParser(pydantic_object=CandidateInfo)
        try:
            # 尝试直接解析
            return parser.parse(output)
        except:
            # 如果agent输出不标准，使用LLM重新结构化
            structured_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="将以下简历信息转换为JSON格式，包含name, skills, score字段。"),
                HumanMessage(content=f"简历信息：\n{output}\n\n请严格输出JSON。")
            ])
            chain = structured_prompt | llm | parser
            return chain.invoke({})
    
    return RunnableLambda(parse_resume)

# ---------- 主流程 ----------
def main():
    # 示例简历文本
    sample_resume = """
    张三
    高级软件工程师 | 5年经验
    
    技能：Python, Java, SQL, 机器学习, Docker
    
    工作经历：
    - 2020-2023 ABC科技 高级后端工程师
      负责微服务架构设计，使用Python和Docker部署
    - 2018-2020 XYZ公司 软件工程师
      参与电商平台开发，使用Java和SQL
    
    项目经验：
    - 智能推荐系统：使用机器学习算法提升转化率30%
    - 分布式日志系统：基于Kubernetes的日志收集方案
    
    教育背景：
    清华大学 计算机科学 硕士
    """
    
    # 初始化模型
    llm = init_model()
    
    # 构建agent
    agent = build_agent(llm)
    
    # 解析简历
    print("开始解析简历...")
    result = agent.invoke(sample_resume)
    
    # 输出结果
    print("\n=== 解析结果 ===")
    print(f"姓名: {result.name}")
    print(f"技能: {', '.join(result.skills)}")
    print(f"评分: {result.score}")
    
    # 输出JSON格式
    print("\n=== JSON格式 ===")
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    main()