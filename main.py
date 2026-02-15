import os
import re
import sys
import pandas as pd
from crewai import Crew
from tools import JobSearchTool, WebScraperTool, read_cv, run_job_search_loop, scrape_url
from agents import create_match_analyst, create_application_expert, create_job_researcher
from tasks import create_analyze_one_job_task, create_cover_letter_one_job_task, create_search_jobs_task
from dotenv import load_dotenv

load_dotenv()
# Avoid UnicodeEncodeError on Windows console
if getattr(sys.stdout, "encoding", "").lower() in ("cp1252", "cp850", "ascii", ""):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Minimum jobs to search for (loop until we have at least this many)
MIN_JOBS = int(os.getenv("MAX_JOBS", "10"))
SCORE_THRESHOLD = 70


def _parse_analysis_output(raw: str) -> tuple[int, str, str]:
    """Parse 'Score: N | Category: X | Tech Stack: Y' from analyst output. Returns (score, category, tech_stack)."""
    score, category, tech_stack = 0, "N/A", "N/A"
    raw = (raw or "").strip()
    if "Score:" in raw:
        m = re.search(r"Score:\s*(\d+)", raw, re.I)
        if m:
            score = min(100, max(0, int(m.group(1))))
    if "Category:" in raw:
        m = re.search(r"Category:\s*([^|]+?)(?:\s*\|\s*Tech|$)", raw, re.I | re.DOTALL)
        if m:
            category = m.group(1).strip()
    if "Tech Stack:" in raw:
        m = re.search(r"Tech Stack:\s*(.+?)(?:\n|$)", raw, re.I | re.DOTALL)
        if m:
            tech_stack = m.group(1).strip()
    return score, category, tech_stack


def _parse_search_output(raw: str) -> list[dict]:
    """Parse list of jobs from researcher output. Expects lines with Title, Company, URL."""
    jobs = []
    # Try to find URL, then Title and Company nearby
    # Regex to find URLs: https?://\S+
    # We look for blocks separated by entries
    blocks = re.split(r"\d+\.\s+|- \s+|Job \d+:", raw)
    for block in blocks:
        if not block.strip(): continue
        url_match = re.search(r"https?://[^\s\)]+", block)
        if url_match:
            url = url_match.group(0).strip()
            # Try to extract title and company from the rest of the block
            title = "Unknown Job"
            company = "N/A"
            
            # Simple heuristic: look for TITLE: ... and COMPANY: ...
            tm = re.search(r"Title:\s*(.+)", block, re.I)
            cm = re.search(r"Company:\s*(.+)", block, re.I)
            if tm: title = tm.group(1).split("\n")[0].strip()
            if cm: company = cm.group(1).split("\n")[0].strip()
            
            # Fallback if no explicit labels
            if title == "Unknown Job":
                lines = [l.strip() for l in block.split("\n") if l.strip() and "http" not in l]
                if lines: title = lines[0]
            
            jobs.append({"title": title, "company": company, "url": url})
    
    # Second pass if first one failed to find specific labels
    if not jobs:
        # Just find all URLs and take the line before or same line as title
        urls = re.findall(r"(https?://[^\s\)]+)", raw)
        for url in urls:
            jobs.append({"title": "Job Posting", "company": "N/A", "url": url})
            
    return jobs


def main():
    print("--- Starting Job Search Automation Agent (loop mode) ---")

    # 1. Load CV and Conditions
    cv_path = "cv.txt"
    if not os.path.exists(cv_path):
        cv_path = "cv.pdf"
    cv_content = read_cv(cv_path)
    if "Error" in cv_content:
        print(cv_content)
        print("Please ensure cv.txt or cv.pdf exists in the project root.")
        return

    conditions_path = "conditions.txt"
    conditions_data = {
        "city": "Remote",
        "job_titles": "Software Engineer",
        "tech_stack": "",
        "work_condition": "Remote",
        "salary": "N/A",
        "other": "",
    }
    if os.path.exists(conditions_path):
        with open(conditions_path, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    key, val = line.split(":", 1)
                    key, val = key.strip().lower(), val.strip()
                    if "city" in key:
                        conditions_data["city"] = val
                    elif "job title" in key:
                        conditions_data["job_titles"] = val
                    elif "tech stack" in key or "tech stacks" in key:
                        conditions_data["tech_stack"] = val
                    elif "work condition" in key:
                        conditions_data["work_condition"] = val
                    elif "salary" in key:
                        conditions_data["salary"] = val
                    elif "other" in key:
                        conditions_data["other"] = val
    else:
        print("Warning: conditions.txt not found. Using default preferences.")

    job_titles = conditions_data["job_titles"]
    city = conditions_data["city"]
    print(f"Conditions loaded: {job_titles} in {city}")

    # 2. Use Job Researcher Agent to find jobs based on CV
    print("--- Researcher: Finding jobs via company career pages ---")
    search_tool = JobSearchTool()
    scraper_tool = WebScraperTool()
    researcher = create_job_researcher([search_tool, scraper_tool])
    search_task = create_search_jobs_task(researcher, cv_content, conditions_data)
    
    crew_search = Crew(agents=[researcher], tasks=[search_task], verbose=True)
    out_search = crew_search.kickoff()
    raw_search = out_search.raw if hasattr(out_search, "raw") else str(out_search)
    
    jobs = _parse_search_output(raw_search)
    print(f"--- Researcher found {len(jobs)} potential jobs ---")
    if not jobs:
        print("No jobs found by researcher. Agent output was:")
        print(raw_search[:500])
        return

    # 3. Agents (no tools needed for per-job analyze/cover letter)
    analyst = create_match_analyst([])
    expert = create_application_expert()

    # 4. Process each job: scrape -> analyze -> cover letter if score >= 70
    results = []
    for i, job in enumerate(jobs):
        title, company, url = job.get("title", "N/A"), job.get("company", "N/A"), job.get("url", "")
        safe_title = title.encode("ascii", "replace").decode() if isinstance(title, str) else str(title)
        print(f"--- Job {i+1}/{len(jobs)}: {safe_title} ---")
        desc = scrape_url(url)
        if desc.startswith("Error"):
            print(f"  Skip (scrape failed): {desc[:80]}")
            results.append({
                "Job Title": title, "Company": company, "URL": url,
                "Summary": "Scrape failed", "Category": "N/A", "Tech Stack": "N/A", "Cover Letter": "N/A",
            })
            continue

        analyze_task = create_analyze_one_job_task(analyst, title, company, url, desc, cv_content)
        crew_analyze = Crew(agents=[analyst], tasks=[analyze_task], verbose=False)
        out_analyze = crew_analyze.kickoff()
        raw_analysis = out_analyze.raw if hasattr(out_analyze, "raw") else str(out_analyze)
        score, category, tech_stack = _parse_analysis_output(raw_analysis)
        summary = f"Score: {score}. {category}. Tech: {tech_stack}"

        cover_letter = "N/A"
        if score >= SCORE_THRESHOLD:
            cover_task = create_cover_letter_one_job_task(expert, title, company, desc, cv_content)
            crew_cover = Crew(agents=[expert], tasks=[cover_task], verbose=False)
            out_cover = crew_cover.kickoff()
            cover_letter = out_cover.raw if hasattr(out_cover, "raw") else str(out_cover)
            cover_letter = (cover_letter or "").strip()[:8000]

        results.append({
            "Job Title": title,
            "Company": company,
            "URL": url,
            "Summary": summary,
            "Category": category,
            "Tech Stack": tech_stack,
            "Cover Letter": cover_letter,
        })

    # 5. Save to Excel
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "job_applications.xlsx")
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)
    print(f"--- Results saved to {output_file} ({len(results)} rows) ---")


if __name__ == "__main__":
    main()
