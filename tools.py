import os
import pandas as pd
from datetime import datetime
from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from duckduckgo_search import DDGS
from pypdf import PdfReader
from bs4 import BeautifulSoup

# Resolve project root (directory where this file lives) for reliable CSV path
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VISITED_URLS_FILE = os.path.join(_PROJECT_ROOT, "visited_urls.csv")


def _run_job_search(max_results: int, visited_urls: set, search_query: str) -> tuple[list[dict], str | None]:
    """Run DDGS text search. Returns (results_found, error_message)."""
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(search_query, max_results=20))
    except Exception as e:
        return [], f"Search failed: {type(e).__name__}: {e}"

    if not raw_results:
        print(f"--- SEARCH: API returned 0 raw results for query ---")
        return [], None

    results_found = []
    for r in raw_results:
        url = r.get("href") or r.get("link")
        if url and url not in visited_urls:
            results_found.append({
                "url": url,
                "title": r.get("title", "Job Post"),
                "body": r.get("body", r.get("snippet", ""))
            })
            if len(results_found) >= max_results:
                break
    return results_found, None


class JobSearchTool(BaseTool):
    name: str = "Job Search Tool"
    description: str = "Searches for job postings using DuckDuckGo. Handles duplicate prevention by checking visited_urls.csv."

    def _run(self, query: str) -> str:
        max_results = 10
        visited_urls = set()
        visited_file = VISITED_URLS_FILE

        if os.path.exists(visited_file):
            try:
                df = pd.read_csv(visited_file)
                col = "url" if "url" in df.columns else df.columns[0]
                visited_urls = set(df[col].dropna().astype(str).tolist())
            except Exception:
                pass

        search_query = query.strip().replace('"', "").strip()
        if not search_query:
            return "Error: empty search query. Provide a company name or search terms."

        print(f"--- TOOL: Searching for: {search_query} ---")

        results_found, err = _run_job_search(max_results, visited_urls, search_query)
        if err:
            print(f"--- TOOL ERROR: {err} ---")
            return f"No job postings found. {err} Try again or use a different query (e.g. 'Software Engineer Stockholm jobs')."

        if not results_found:
            # Search succeeded but all URLs were already visited
            print(f"--- TOOL: Search returned results but all {len(visited_urls)} URLs already in visited_urls.csv ---")
            return (
                "No new job postings (all results were already in visited_urls.csv). "
                "Try a different search query or delete visited_urls.csv to reset."
            )

        new_data = []
        output_lines = []
        for res in results_found:
            output_lines.append(f"Title: {res['title']}\nURL: {res['url']}\nSnippet: {res['body']}\n---")
            new_data.append({"url": res["url"], "date": datetime.now().strftime("%Y-%m-%d")})

        df_new = pd.DataFrame(new_data)
        write_header = not os.path.exists(visited_file)
        df_new.to_csv(visited_file, mode="a", header=write_header, index=False)

        print(f"--- TOOL: Found {len(results_found)} new jobs, saved to {visited_file} ---")
        return "\n".join(output_lines)


def run_job_search_loop(
    queries: list[str],
    min_results: int = 10,
    max_per_query: int = 15,
) -> list[dict]:
    """
    Run search for each query until we have at least min_results jobs.
    Returns list of {"title", "company", "url"} and appends new URLs to visited_urls.csv.
    """
    visited_file = VISITED_URLS_FILE
    visited_urls = set()
    if os.path.exists(visited_file):
        try:
            df = pd.read_csv(visited_file)
            col = "url" if "url" in df.columns else df.columns[0]
            visited_urls = set(df[col].dropna().astype(str).tolist())
        except Exception:
            pass

    all_jobs = []
    seen_urls = set(visited_urls)

    for q in queries:
        if len(all_jobs) >= min_results:
            break
        search_query = q.strip().replace('"', "").strip()
        if not search_query or "job" not in search_query.lower():
            search_query = f"{search_query} jobs"
        print(f"--- SEARCH: {search_query} ---")
        results_found, err = _run_job_search(max_per_query, seen_urls, search_query)
        if err:
            print(f"--- SEARCH ERROR: {err} ---")
            continue
        for r in results_found:
            url = r["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = r.get("title", "Job Post")
            body = r.get("body", "")
            company = "N/A"
            if " at " in title:
                parts = title.split(" at ", 1)
                if len(parts) == 2:
                    title, company = parts[0].strip(), parts[1].strip()
            all_jobs.append({"title": title, "company": company, "url": url})
            if len(all_jobs) >= min_results:
                break

        if results_found:
            new_data = [{"url": res["url"], "date": datetime.now().strftime("%Y-%m-%d")} for res in results_found]
            df_new = pd.DataFrame(new_data)
            write_header = not os.path.exists(visited_file)
            df_new.to_csv(visited_file, mode="a", header=write_header, index=False)
            print(f"--- SEARCH: Got {len(results_found)} results, total jobs so far: {len(all_jobs)} ---")

    return all_jobs


def scrape_url(url: str) -> str:
    """Scrape a single URL and return text content (first 5000 chars)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            stealth = Stealth()
            stealth.apply_stealth_sync(page)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            content = page.content()
            browser.close()
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:5000]
    except Exception as e:
        return f"Error scraping URL: {str(e)}"


class WebScraperTool(BaseTool):
    name: str = "Web Scraper Tool"
    description: str = "Scrapes the content of a job posting URL to extract detailed requirements."

    def _run(self, url: str) -> str:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Apply stealth
                stealth = Stealth()
                stealth.apply_stealth_sync(page)
                
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for main content or common job containers
                page.wait_for_timeout(2000)
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Clean up script and style elements
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                
                text = soup.get_text(separator=' ', strip=True)
                browser.close()
                return text[:5000] # Return first 5000 characters to avoid context overflow
        except Exception as e:
            return f"Error scraping URL: {str(e)}"

def read_cv(file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Error: CV file not found at {file_path}"
    
    if file_path.endswith('.pdf'):
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading text file: {str(e)}"
