# Week 2: AI Component

## Project Overview
The goal of this project is to build an automated, intelligent pipeline that processes job listings and candidate resumes to analyze technical skill gaps. The system utilizes Local LLMs or Gemini to:
1. Parse and extract technical stacks from job descriptions in batch mode and tag them in a local SQLite database.
2. Extract the technical stack of a candidate from a resume text file, cross-reference it with the accumulated required skills in the database, and return a nearly accurate set of missing skills.

## Setup Instructions

### Prerequisites
* **API Key**: A Gemini API Key from [Google AI Studio](https://aistudio.google.com/api-keys).
* **Package Manager**: [uv](https://github.com/astral-sh/uv) (a fast Python package installer and resolver).

### Environment Setup
1. Clone the repository and navigate to the week2 directory
2. Copy the example environment template and add your Gemini API key:
   ```bash
   cp .env.example .env
   ```
   Open the `.env` file and set the key:
   ```env
   GEMINI_API_KEY="your-actual-api-key-here"
   ```

3. Run `uv sync` for the first time to setup the project dependencies and you are good to go.

## Usage

### 1. Job Tagging (`tag_data.py`)
Populates the `tech_stack` column in the `jobs` table with the technical skills extracted from the `description` column.
```bash
uv run python tag_data.py [database_path] [model_name]
```
* **Parameters**: (Both optional)
  - `database_path`: Defaults to `data/jobs_d3_eval.db`
  - `model_name`: Defaults to `gemini-3.1-flash-lite`

### 2. Skill Gap Analysis (`find_skill_gaps.py`)
It profiles the candidate's resume against all the required job skills to identify missing skills.
```bash
uv run python find_skill_gaps.py [resume_path] [model_name] [database_path]
```
* **Parameters**: (All optional)
  - `resume_path`: Defaults to `data/resume_d3_eval.txt`
  - `model_name`: Defaults to `gemini-3.1-flash-lite`
  - `database_path`: Defaults to `data/jobs_d3_eval.db`

## API / Function Reference

#### `find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`
* **Purpose**: Orchestrates reading candidate resume data, fetching job requirements, comparing skills, and returning gaps.
* **Inputs**:
  - `input_file_path` (str): Path to candidate resume file.
  - `db_url` (str): Path to the jobs database.
* **Outputs**:
  - `SkillGapResult`: A Pydantic model wrapping `gaps` (a sorted, lowercase list of missing skills).

---

#### `tag_data(db_url: str)`
* **Purpose**: Populates the `tech_stack` column in the `jobs` table with the technical skills extracted from the `description` column.
* **Inputs**:
  - `db_url` (str): Path to the jobs database.
* **Outputs**:
  - `None`

## Data / Assumptions

### Database Schema
* The database contains a `jobs` table with:
  - `source_id` (INTEGER, Primary Key)
  - `job_title` (TEXT, the job title)
  - `company` (TEXT, the company name)
  - `description` (TEXT, raw job description)
  - `tech_stack` (TEXT, comma-separated list of required technical skills)

### Assumptions & Normalization
* **Resume Parsing**: The LLM is instructed to output skills strictly as a comma-separated single line.
* **Delimiters**: Tech stacks are separated by commas.
* **Slash Splitting**: The slash (`/`) character is treated as an OR operator (e.g. `mysql/postgresql` yields `mysql` and `postgresql`), except for established terms containing slashes such as `ci/cd` and `a/b testing`.

### Data Flow
1. **Resume Input & DB Querying** -> Resume text is loaded, and job records are fetched in batches.
2. **AI Extraction** -> LLM profiles the resume skills.
3. **Database Extraction** -> Required database skills are compiled and split where appropriate.
4. **Set Difference** -> Comparison retrieves the skills present in the database requirements but absent in the resume.

## Testing
- My system is tested to ensure I can use both Local Models and Cloud Models like Gemini. And handling missing files like the database or the resume file.
* Multi Model Support
  - `uv run python tag_data.py data/jobs.db phi3`
  - `uv run python tag_data.py data/jobs.db gemini-3-flash-preview`
* For missing file handling, try removing the jobs database file `data/jobs.db` or the resume file `data/resume.txt`. The system should handle these cases gracefully.


## Limitations
* **LLM Inaccuracy**: The LLM might extract inaccurately for tech stacks with abbreviations.
* **String Matching Limitations**: Simple string matching can miss partial matches or misidentify abbreviations.
* **Network & Rate Limits**: Heavy reliance on third-party APIs can cause latency or transient 503 throttling errors.

## Architecture Reflection

### Design Choices
* **Modularity**: Extracted LLM orchestration into `prompt_model.py` and decoupled candidate resume profiling from job requirement collation.
* **Safe Operations**: Wrapped database connection state in `try-finally` structures to guarantee closure and prevent connection leaks.

### Trade-offs
* **Simplicity vs. Deep Parsing**: We chose a straightforward string splitting and string matching mechanism over a heavy semantic search model. This prioritizes speed and light computing resource requirements, but lacks synonym consolidation (e.g., matching `postgres` to `postgresql` dynamically).
* **Batch Database Commits**: Rather than writing to the SQLite database per row, `tag_data.py` batches writes. This increases I/O efficiency but might lose intermediate state if a crash occurs mid-batch.

### Improvements
* **Better LLM**: Use a better LLM for tagging data.
* **Better Prompt**: Use a better prompt for tagging data.