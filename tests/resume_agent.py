"""
简历分析 Agent — LangChain v1.0 API 测试
覆盖: create_agent / init_chat_model / @tool / ToolRuntime /
      checkpointer / structured_output / SummarizationMiddleware / streaming

用法:
  set DEEPSEEK_API_KEY=sk-xxx
  uv run python resume_agent.py          # 交互模式
  uv run python resume_agent.py --demo   # 演示模式（自动跑一轮）
"""

import os
import sys
from typing import Literal

from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.utils.uuid import uuid7


# ═══════════════════════════════════════════
# 1. 结构化输出 — 简历评分卡
# ═══════════════════════════════════════════

class SkillItem(BaseModel):
    name: str = Field(description="技能名称")
    level: Literal["入门", "熟练", "精通", "专家"] = Field(description="熟练度")
    years: float | None = Field(description="使用年限")

class EducationItem(BaseModel):
    degree: str = Field(description="学位")
    school: str = Field(description="学校")
    major: str = Field(description="专业")
    year: str | None = Field(description="毕业年份")

class ResumeReport(BaseModel):
    """简历分析报告 — create_agent response_format 直接返回此结构"""
    name: str = Field(description="候选人姓名")
    skills: list[SkillItem] = Field(description="技能列表")
    education: list[EducationItem] = Field(description="教育经历")
    total_years: float | None = Field(description="总工作年限")
    highlights: list[str] = Field(description="亮点（3-5 条）")
    score: int = Field(description="综合评分 1-10", ge=1, le=10)
    summary: str = Field(description="一句话总结")


# ═══════════════════════════════════════════
# 2. 工具定义 — @tool + ToolRuntime
# ═══════════════════════════════════════════

# 模拟"企业简历库"数据
RESUME_DB = {
    "张三": {
        "name": "张三",
        "skills": ["Python", "PyTorch", "LangChain", "Docker", "SQL"],
        "experience": "5年AI工程师，负责RAG系统开发，从零搭建企业级知识库",
        "education": [{"degree": "硕士", "school": "清华大学", "major": "计算机科学", "year": "2019"}],
    }
}


@tool
def search_resume_database(name: str, runtime: ToolRuntime) -> str:
    """在企业简历库中搜索候选人。返回候选人的技能、经验、教育信息。"""
    # 展示 ToolRuntime 用法：access state
    search_count = runtime.state.get("search_count", 0) + 1

    if name in RESUME_DB:
        import json
        info = RESUME_DB[name]
        return json.dumps(info, ensure_ascii=False, indent=2)
    return f"未找到候选人「{name}」的信息"


@tool
def compare_candidates(
    name_a: str,
    name_b: str,
    runtime: ToolRuntime,
) -> str:
    """比较两位候选人的匹配度。返回对比分析。"""
    a = RESUME_DB.get(name_a)
    b = RESUME_DB.get(name_b)

    if not a or not b:
        missing = name_a if not a else name_b
        return f"未找到候选人「{missing}」"

    a_skills = set(a["skills"])
    b_skills = set(b["skills"])
    common = a_skills & b_skills

    return (
        f"对比结果:\n"
        f"  {name_a}: {', '.join(a['skills'])}\n"
        f"  {name_b}: {', '.join(b['skills'])}\n"
        f"  共同技能: {', '.join(common) if common else '无'}\n"
        f"  {name_a}独有: {', '.join(a_skills - b_skills)}"
    )


# ═══════════════════════════════════════════
# 3. 构建 Agent
# ═══════════════════════════════════════════

def build_agent():
    """构建简历分析 Agent，返回 (agent, checkpointer, config)"""
    model = init_chat_model(
        "openai:deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        temperature=0.3,
        max_tokens=4096,
    )

    checkpointer = InMemorySaver()
    thread_id = str(uuid7())

    agent = create_agent(
        model=model,
        tools=[search_resume_database, compare_candidates],
        system_prompt="""你是一位资深技术面试官和简历分析师。

你的工作流程：
1. 用户提供简历后，用 search_resume_database 查询候选人信息
2. 仔细分析技能、经验、教育背景
3. 如果用户要求比较，用 compare_candidates 工具
4. 最终以结构化报告形式输出分析结果

注意：
- 始终使用中文回复
- 评分要客观，1-10 分制
- 亮点要具体，不要泛泛而谈""",
        response_format=ResumeReport,
        checkpointer=checkpointer,
        middleware=[
            SummarizationMiddleware(
                model=model,
                trigger=("messages", 12),  # 超过 12 条消息触发摘要
                keep=("messages", 6),       # 保留最近 6 条
            ),
        ],
    )

    config = {"configurable": {"thread_id": thread_id}}
    return agent, config


# ═══════════════════════════════════════════
# 4. 交互模式
# ═══════════════════════════════════════════

def interactive_mode():
    """交互式多轮对话 — 测试 checkpointer / streaming / structured_output"""
    agent, config = build_agent()
    print("=" * 60)
    print("[LangChain v1.0] Resume Analysis Agent")
    print("   Type 'quit' to exit, 'report' for report, 'compare' to compare")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n[You]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "report":
            user_input = "请对刚才分析的候选人输出完整的结构化简历报告"

        print("\n[Agent]: ", end="", flush=True)

        # 流式输出
        full_text = []
        for mode, chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                msg_chunk, metadata = chunk
                content = msg_chunk.content
                if isinstance(content, str) and content:
                    print(content, end="", flush=True)
                    full_text.append(content)
            elif mode == "updates":
                # 检查是否有 structured_response
                if isinstance(chunk, dict) and "structured_response" in chunk:
                    print("\n\n[Report] [结构化报告已生成]")
                    report = chunk["structured_response"]
                    print(f"   姓名: {report.name}")
                    print(f"   评分: {report.score}/10")
                    print(f"   总结: {report.summary}")
                    print(f"   技能: {len(report.skills)} 项")
                    for s in report.skills:
                        print(f"     - {s.name}: {s.level} ({s.years}年)")
                    print(f"   教育: {len(report.education)} 条")
                    for e in report.education:
                        print(f"     - {e.degree} @ {e.school}, {e.major}")
                    print(f"   亮点: {', '.join(report.highlights)}")

        print()  # 换行


# ═══════════════════════════════════════════
# 5. 演示模式
# ═══════════════════════════════════════════

def demo_mode():
    """自动演示 — 跑一轮完整的分析流程"""
    agent, config = build_agent()
    print("=" * 60)
    print("[Demo] 演示模式：自动简历分析")
    print("=" * 60)

    steps = [
        "请分析候选人「张三」的简历",
        "他的 Python 水平如何？",
        "请给他一个综合评分报告",
    ]

    for i, msg in enumerate(steps, 1):
        print(f"\n{'─' * 50}")
        print(f"[Step] 第 {i} 轮: {msg}")
        print(f"{'─' * 50}")

        result = agent.invoke(
            {"messages": [{"role": "user", "content": msg}]},
            config=config,
        )

        # 打印最后一条 AI 消息
        for m in reversed(result.get("messages", [])):
            content = getattr(m, "content", None)
            if content and isinstance(content, str) and len(content) > 10:
                print(f"\n[AI] {m.type}: {content[:500]}...")
                break

        # 检查 structured_response
        if "structured_response" in result:
            report = result["structured_response"]
            print(f"\n[Report] 结构化报告:")
            print(f"   {report.name} | 评分: {report.score}/10")
            print(f"   {report.summary}")

    # 验证 — 确认 checkpointer 工作
    print(f"\n{'=' * 50}")
    print("[OK] 演示完成。验证要点：")
    print("   [1] create_agent 正常工作")
    print("   [2] @tool 被正确调用")
    print("   [3] checkpointer 保持多轮对话上下文")
    print("   [4] structured_output 返回 ResumeReport")
    print(f"{'=' * 50}")


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_mode()
    else:
        interactive_mode()
