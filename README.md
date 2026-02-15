# Job Search Automation Agent

A CrewAI-based automation system that searches for job postings, analyzes them against your CV, and generates tailored cover letters. This system is designed to run 100% locally using Ollama but also supports online LLMs (OpenAI, Gemini).

## 🚀 Features

- **Automated Research**: Scrapes LinkedIn, Indeed, and Google Jobs using Playwright and DuckDuckGo (target: 40+ jobs).
- **Duplicate Prevention**: Tracks all visited URLs in `visited_urls.csv` to avoid re-checking identical postings.
- **Deep Analysis**: Automatically identifies **Job Category** and **Tech Stack** for every listing.
- **Tailored Applications**: Generates professional, personalized cover letters for high-matching jobs.
- **Local-First**: Built to run locally using Ollama for privacy and zero cost.
- **Rich Excel Export**: Saves structured results [Title, Company, URL, Category, Tech Stack, Cover Letter] to `job_applications.xlsx`.

## 🛠️ Tech Stack

- **Framework**: [CrewAI](https://www.crewai.com/)
- **LLM**: Ollama (Llama 3/Mistral), OpenAI (GPT-4o), or Google Gemini.
- **Web Scraping**: [Playwright](https://playwright.dev/python/) with Stealth mode.
- **Data Handling**: Pandas & OpenPyXL.
- **Utility**: Python-dotenv, PyPDF, BeautifulSoup4.

## 📋 Project Structure

- `main.py`: The orchestrator that coordinates agents and tasks.
- `agents.py`: Definition of agents (Job Researcher, Match Analyst, Application Expert).
- `tasks.py`: Specific task definitions for the agents.
- `tools.py`: Custom scraping and searching tools.
- `requirements.txt`: Project dependencies.

## ⚙️ Setup Instructions

### 1. Environment Setup

Create and manage the virtual environment based on your operating system:

#### **Windows (PowerShell)**
```powershell
# Create the environment
python -m venv .venv

# Activate the environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Deactivate when done
deactivate
```

#### **Linux & macOS**
```bash
# Create the environment
python3 -m venv .venv

# Activate the environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Deactivate when done
deactivate
```

### 2. Prepare Your Files
Place your CV and job preferences in the project root folder:
- **CV**: Name it `cv.txt` or `cv.pdf`.
- **Conditions**: Create `conditions.txt`. It MUST follow this format for best results:
  ```text
  Job Title: Senior Backend Engineer, Team Lead
  City: Stockholm, Sweden
  Work Condition: Remote or Hybrid
  Tech Stack: Java, Spring Boot, Kafka, AWS
  Desired Salary: 80,000 - 120,000 EUR
  Other: Any other preferences here...
  ```

### 3. LLM Configuration

The agent uses a flexible configuration. You can switch between providers by editing the `.env` file.

#### **Environment Variables**
| Variable | Description | Example |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | The LLM provider to use | `ollama`, `gemini`, `openai` |
| `MODEL_NAME` | The specific model name | `smollm:135m`, `llama3.2`, `gemini-2.0-flash` |
| `MAX_JOBS` | Minimum number of jobs to find | `40` |

#### **Setup Examples**

**Local (Ollama - Recommended)**
1. **Install Ollama**: Download from [ollama.com](https://ollama.com/).
2. **Download Model**: Run any of these commands:
   - `ollama pull smollm:135m` (Ultra-lightweight, fastest)
   - `ollama pull llama3.2` (Lightweight/Mini version)
   - `ollama pull llama3` (High performance)
3. **Configure .env**:
   ```env
   LLM_PROVIDER=ollama
   MODEL_NAME=smollm:135m # Ultra-lightweight version
   ```

**Online (Gemini)**
1. **Configure .env**:
   ```env
   LLM_PROVIDER=gemini
   MODEL_NAME=gemini-2.0-flash
   GEMINI_API_KEY=your_key_here
   ```

**Online (OpenAI)**
1. **Configure .env**:
   ```env
   LLM_PROVIDER=openai
   MODEL_NAME=gpt-4o
   OPENAI_API_KEY=your_key_here
   ```

Refer to [.env.example](file:///c:/Users/masoud.vafaei/project/aiagentJob/.env.example) for a full template.

## 🏃 Execution

Run the agent with:
```powershell
.\.venv\Scripts\python main.py
```

## 📊 Output & Persistence

### **Excel Report**
The final report is generated in the project root as **`job_applications.xlsx`**. It contains the following columns for every processed job:
- **Job Title**: The official title of the position.
- **Company**: The hiring organization.
- **URL**: Direct link to the job posting.
- **Category**: The sector or branch (e.g., Software Engineering).
- **Tech Stack**: Extracted technologies (e.g., Python, Docker).
- **Summary**: A brief overview of the role and its fit.
- **Cover Letter**: A fully tailored application letter.

### **Visited URLs**
To save time and API quota, the agent maintain **`visited_urls.csv`**. 
- It logs every URL encountered and the date of discovery.
- In future runs, the agent will automatically skip any URL present in this file, ensuring you always see fresh opportunities.
- To reset your history, simply delete `visited_urls.csv`.


