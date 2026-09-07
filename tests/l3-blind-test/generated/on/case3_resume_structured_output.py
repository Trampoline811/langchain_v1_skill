from typing import List, Optional
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.agents.structured_output import ToolStrategy


class CandidateInfo(BaseModel):
    """Structured output schema for parsed resume."""
    name: str = Field(description="Full name of the candidate")
    skills: List[str] = Field(description="List of technical skills mentioned")
    score: int = Field(description="Overall candidate score from 0 to 100")


def init_model() -> str:
    """Initialize and return the chat model identifier."""
    # Using OpenAI GPT-4o as an example; swap with any supported provider/model
    return "openai:gpt-4o"


def build_agent(model: str):
    """Build and return the resume parsing agent."""
    agent = create_agent(
        model=model,
        system_prompt=(
            "You are an expert resume parser. Extract the candidate's name, "
            "technical skills, and provide an overall score (0-100) based on "
            "experience, skill relevance, and achievements."
        ),
        response_format=ToolStrategy(
            schema=CandidateInfo,
            handle_errors=True,
        ),
    )
    return agent


if __name__ == "__main__":
    # --- Initialize model and build agent ---
    model_id = init_model()
    agent = build_agent(model_id)

    # --- Example resume text ---
    resume_text = """
    John Doe
    Senior Python Developer with 8 years of experience.
    Skills: Python, FastAPI, LangChain, PostgreSQL, Docker, AWS.
    Led a team of 5 engineers to build a scalable microservices platform.
    """

    # --- Invoke the agent ---
    result = agent.invoke(
        {"messages": [{"role": "user", "content": resume_text}]}
    )

    # --- Extract structured response ---
    candidate: CandidateInfo = result["structured_response"]
    print(f"Name: {candidate.name}")
    print(f"Skills: {', '.join(candidate.skills)}")
    print(f"Score: {candidate.score}")