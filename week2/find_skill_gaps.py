import sys
import sqlite3
from typing import List
from pathlib import Path
from pydantic import BaseModel
from prompt_model import prompt_model


class SkillGapResult(BaseModel):
    gaps: List[str]


DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_DB_PATH = "data/jobs_d3_eval.db"
DEFAULT_RESUME_PATH = "data/resume_d3_eval.txt"


def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:
    resume_path = Path(input_file_path)
    if not resume_path.exists():
        print(f"Error: '{input_file_path}' not found.")
        sys.exit(1)
    db_path = Path(db_url)
    if not db_path.exists():
        print(f"Error: '{db_url}' not found.")
        sys.exit(1)
    try:
        resume_text = resume_path.read_text(encoding="utf-8")
        resume_skills = get_resume_skills(DEFAULT_MODEL, resume_text)
        conn = sqlite3.connect(str(db_path))
        try:
            db_skills = get_db_skills(conn)
        finally:
            conn.close()
        return SkillGapResult(gaps=sorted(db_skills - resume_skills))
    except Exception as e:
        print(f"[Error] Failed to calculate skill gaps: {str(e)}")
        return SkillGapResult(gaps=[])


def get_resume_skills(model_name: str, resume_text_norm: str) -> set[str]:
    prompt = (
        "You are an expert data labeling assistant. Analyze the following candidate resume "
        "and extract the technical stack of the candidate.\n"
        "Include programming languages, frameworks, libraries, databases, tools, APIs, cloud platforms, "
        "and methodologies (e.g., A/B testing, CI/CD, code reviews, testing, databases, APIs) "
        "that the candidate has experience in.\n\n"
        "You MUST output the result ONLY as a single line containing a comma-separated list of the technical stack, "
        'for example: "Java, Python, Docker, CI/CD, SQL".\n'
        "Do not include any introductory/concluding text, markdown, or formatting.\n\n"
        f"Resume:\n{resume_text_norm}"
    )

    try:
        response = prompt_model(model_name, prompt)
        error_tags = ("[Error]", "[Gemini Error]", "[Ollama Error]")
        if response.startswith(error_tags):
            raise Exception(f"{response}")
        tech_stack = response.strip()
        if not tech_stack:
            return set()
        return {part.strip().lower() for part in tech_stack.split(",") if part.strip()}
    except Exception as e:
        print(f"[Resume Tech Stack Extraction] Error: {str(e)}")
        sys.exit(1)


def get_db_skills(conn) -> set[str]:
    cursor = conn.cursor()
    required_skills = set()
    last_source_id = 0
    batch_size = 5
    while True:
        cursor.execute(
            """
            SELECT source_id, tech_stack 
            FROM jobs 
            WHERE tech_stack IS NOT NULL 
              AND tech_stack != ''
              AND source_id > ?
            ORDER BY source_id ASC
            LIMIT ?
        """,
            (last_source_id, batch_size),
        )
        rows = cursor.fetchall()
        if not rows:
            break
        for source_id, tech_stack_str in rows:
            skills = []
            for part in tech_stack_str.split(","):
                part = part.strip().lower()
                if not part or part == "n/a":
                    continue
                if part in ("ci/cd", "a/b testing"):
                    skills.append(part)
                elif "/" in part:
                    skills.extend([sp.strip() for sp in part.split("/") if sp.strip()])
                else:
                    skills.append(part)
            required_skills.update(skills)
        last_source_id = rows[-1][0]
    return required_skills


if __name__ == "__main__":
    if len(sys.argv) > 4:
        print(
            "usage: uv run python find_skill_gaps.py [resume_path] [model] [database_path]"
        )
        sys.exit(1)

    if len(sys.argv) >= 2:
        DEFAULT_RESUME_PATH = sys.argv[1]
    if len(sys.argv) >= 3:
        DEFAULT_MODEL = sys.argv[2]
    if len(sys.argv) == 4:
        DEFAULT_DB_PATH = sys.argv[3]

    result = find_skill_gaps(DEFAULT_RESUME_PATH, DEFAULT_DB_PATH)
    print(f"gaps={result.gaps}")
