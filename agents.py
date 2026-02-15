import os
from crewai import Agent, LLM
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    """
    Factory function to get the LLM based on environment variables.
    Checks for LLM_PROVIDER and MODEL_NAME.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model = os.getenv("MODEL_NAME", "llama3")
    
    if provider == "openai":
        return LLM(model=model, api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return LLM(model=f"gemini/{model}", api_key=api_key)
    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return LLM(model=f"ollama/{model}", base_url=base_url)
    else:
        # Fallback to local Ollama if provider is unrecognized
        return LLM(model=f"ollama/{model}", base_url="http://localhost:11434")

llm = get_llm()

def create_job_researcher(tools):
    return Agent(
        role='Job Researcher',
        goal='Identify relevant software companies in target cities, navigate to their career pages, and extract specific job openings that match the user\'s CV.',
        backstory='You are a master of corporate OSINT and career page navigation. You don\'t just look at job boards; you find the sources. You know how to find software companies, startups, and tech giants, and you know exactly where to find their "Careers" or "Jobs" links to get the most up-to-date postings.',
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def create_match_analyst(tools):
    return Agent(
        role='Match Analyst',
        goal='Compare job descriptions with the user\'s CV and score them from 0 to 100 based on fit (skills, experience, location, etc.).',
        backstory='You have a keen eye for detail and understand what recruiters look for. You can accurately assess whether a candidate is a good match for a role.',
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def create_application_expert():
    return Agent(
        role='Application Expert',
        goal='Write highly tailored cover letters for high-scoring jobs and format all application details for final output.',
        backstory='You are a master of professional communication. You know how to highlight a candidate\'s strengths in a way that resonates with hiring managers.',
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
