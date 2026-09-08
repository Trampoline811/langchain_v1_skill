from typing import List, Optional
from pydantic import BaseModel, Field

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent


class CandidateInfo(BaseModel):
    """Structured information extracted from a resume."""
    name: str = Field(description="Full name of the candidate")
    skills: List[str] = Field(description="List of technical and professional skills")
    score: int = Field(description="Overall candidate score from 0 to 100")


def initialize_model():
    """Initialize the chat model."""
    return init_chat_model("openai:gpt-4o", temperature=0.0)


def build_resume_parser_agent(model):
    """Build the resume parsing agent with structured output."""
    return create_agent(
        model=model,
        system_prompt=(
            "You are a resume parsing assistant. "
            "Extract the candidate's name, skills, and an overall score (0-100) "
            "from the provided resume text."
        ),
        response_format=CandidateInfo,
    )


if __name__ == "__main__":
    # Initialize model and build agent
    llm = initialize_model()
    agent = build_resume_parser_agent(llm)

    # Sample resume text
    resume_text = """
    John Doe
    Senior Software Engineer
    
    Skills: Python, FastAPI, LangChain, PostgreSQL, Docker, Kubernetes
    
    Experience:
    - 5 years building backend services
    - Led a team of 4 engineers
    - Designed microservices architecture
    """

    # Invoke the agent
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": f"Parse this resume:\n\n{resume_text}"}
        ]
    })

    # Print structured output
    print(result["structured_response"])