"""
深度研究规划 Agent 示例
- 使用 DeepAgents 构建
- 自定义计算器工具（加/乘）计算研究预算
- 结构化输出研究计划（标题 + 预算 + 步骤列表）
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from deepagents import create_deep_agent
from langchain.tools import tool


# ============================================================
# 1. 结构化输出 Schema
# ============================================================
class ResearchStep(BaseModel):
    """单个研究步骤"""
    description: str = Field(description="步骤描述")
    estimated_hours: float = Field(description="预计耗时（小时）")


class ResearchPlan(BaseModel):
    """研究计划结构化输出"""
    title: str = Field(description="研究计划标题")
    budget: float = Field(description="总预算（美元）")
    steps: List[ResearchStep] = Field(description="研究步骤列表")


# ============================================================
# 2. 自定义计算器工具（加 / 乘）
# ============================================================
@tool
def add_numbers(a: float, b: float) -> float:
    """将两个数字相加。"""
    return a + b


@tool
def multiply_numbers(a: float, b: float) -> float:
    """将两个数字相乘。"""
    return a * b


# ============================================================
# 3. 模型初始化（独立函数）
# ============================================================
def init_model() -> ChatOpenAI:
    """
    初始化语言模型。
    使用硅基流动（SiliconFlow）免费模型，兼容 OpenAI 接口。
    请将 SILICONFLOW_API_KEY 设置为环境变量。
    """
    import os

    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 SILICONFLOW_API_KEY")

    return ChatOpenAI(
        model="THUDM/glm-4-9b-chat",  # 免费模型，128K 上下文，支持 Tools
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
        temperature=0.2,
    )


# ============================================================
# 4. Agent 构建（独立函数）
# ============================================================
def build_research_agent(model: ChatOpenAI):
    """
    构建深度研究规划 Agent。
    - 注入计算器工具（加/乘）
    - 配置结构化输出（ResearchPlan）
    """
    system_prompt = """
你是一位资深研究规划专家。你的任务：
1. 根据用户的研究主题，先使用计算器工具（add_numbers / multiply_numbers）估算研究预算。
   预算估算逻辑示例：
   - 基础费用 = 每小时费率 × 预计总工时
   - 若研究涉及多阶段，可累加各阶段费用
   - 可乘以一个风险系数（如 1.2）得到最终预算
2. 将最终预算与完整研究计划以结构化 JSON 返回，字段必须匹配 ResearchPlan schema：
   - title: 研究计划标题
   - budget: 总预算（美元，数字）
   - steps: 步骤列表，每步含 description 与 estimated_hours

请务必先调用计算器工具完成预算计算，再输出最终计划。
""".strip()

    agent = create_deep_agent(
        model=model,
        tools=[add_numbers, multiply_numbers],
        system_prompt=system_prompt,
        response_format=ResearchPlan,  # 结构化输出
    )
    return agent


# ============================================================
# 5. 主入口
# ============================================================
if __name__ == "__main__":
    # 初始化模型
    llm = init_model()

    # 构建 Agent
    research_agent = build_research_agent(llm)

    # 单轮示例调用
    user_request = (
        "我想研究《大语言模型在医疗领域的应用与伦理挑战》，"
        "预计需要 3 个阶段：文献综述（40 小时）、实验设计（30 小时）、"
        "伦理分析（20 小时）。每小时费率 50 美元，"
        "请计算总预算（含 1.2 倍风险系数）并给出完整研究计划。"
    )

    result = research_agent.invoke(
        {"messages": [HumanMessage(content=user_request)]}
    )

    # 打印最终回复
    print("\n===== Agent 最终回复 =====")
    print(result["messages"][-1].content)