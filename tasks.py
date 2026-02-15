import os
from crewai import Task

def create_job_automation_task(researcher, analyst, expert, cv_content, conditions):
    """
    Combines the process into a single clear instruction set to help smaller LLMs.
    """
    job_titles = conditions.get('job_titles', 'Java Developer')
    city = conditions.get('city', 'Stockholm')
    tech = conditions.get('tech_stack', 'Java')
    
    return Task(
        description=(
            f"STEP 1: Use the Job Search Tool to find 10 '{job_titles}' jobs in '{city}'.\n"
            f"STEP 2: For EACH job found, use the Web Scraper Tool to read the description.\n"
            f"STEP 3: Compare EACH job to this CV:\n{cv_content[:2000]}\n"
            f"STEP 4: If it's a match (Java/Backend), write a cover letter.\n"
            "STEP 5: Provide a JSON list of: [Job Title, Company, URL, Category, Tech Stack, Cover Letter]."
        ),
        expected_output="A JSON list of matches with cover letters.",
        agent=researcher # We can use one agent or a crew, but let's try pushing the researcher to do the loop
    )

def create_search_jobs_task(agent, cv_content, conditions):
    job_titles = conditions.get('job_titles', 'Java Developer')
    city = conditions.get('city', 'Stockholm')
    tech = conditions.get('tech_stack', '')
    
    return Task(
        description=(
            f"1. Analyze the CV to understand the profile: {cv_content[:1000]}\n"
            f"2. Search for lists of software companies, tech startups, or IT firms in '{city}'.\n"
            f"3. For the most relevant companies found, use the Web Scraper Tool to find their 'Careers' or 'Jobs' pages.\n"
            f"4. Scrape those career pages to find specific openings matching '{job_titles}'.\n"
            "5. You MUST find at least 15 potential job URLs from these company websites.\n"
            "6. Return a list of [Title, Company, URL]. Direct company career page URLs are preferred over generic job board links."
        ),
        expected_output="A list of at least 10 job postings found directly on company career pages.",
        agent=agent
    )

def create_analyze_matches_task(agent, cv_content, conditions):
    return Task(
        description=(
            "Take the list of jobs provided. For EACH one, use the Web Scraper Tool to read the full description. "
            f"Check if the candidate is a good fit based on this CV: {cv_content[:1500]}. "
            "Extract 'Job Category' and 'Tech Stack'. Score from 0-100."
        ),
        expected_output="A list of analyzed jobs with scores and tech stacks.",
        agent=agent
    )

def create_generate_application_task(agent):
    return Task(
        description=(
            "For every job that scored above 70, write a tailored cover letter. "
            "Format everything as a JSON list of dictionaries for Excel export."
        ),
        expected_output="A JSON list of completed applications.",
        agent=agent
    )


def create_analyze_one_job_task(agent, job_title: str, company: str, url: str, job_description: str, cv_content: str):
    """Single-job analysis: score 0-100, category, tech stack. Output must be one line: Score: N | Category: X | Tech Stack: Y"""
    return Task(
        description=(
            f"Job: {job_title} at {company}\nURL: {url}\n\nJob description:\n{job_description[:3500]}\n\n"
            f"Candidate CV (excerpt):\n{cv_content[:1500]}\n\n"
            "Score this job fit from 0 to 100. Extract Job Category and Tech Stack. "
            "Reply with exactly one line in this format: Score: <number> | Category: <text> | Tech Stack: <comma-separated>"
        ),
        expected_output="One line: Score: N | Category: X | Tech Stack: Y",
        agent=agent,
    )


def create_cover_letter_one_job_task(agent, job_title: str, company: str, job_description: str, cv_content: str):
    """Generate a single cover letter for one job."""
    return Task(
        description=(
            f"Job: {job_title} at {company}\n\nJob description:\n{job_description[:3500]}\n\n"
            f"Candidate CV (excerpt):\n{cv_content[:1500]}\n\n"
            "Write a professional, tailored cover letter for this job (3-5 short paragraphs). Output only the cover letter text, no labels."
        ),
        expected_output="Cover letter text only.",
        agent=agent,
    )
