import sys
import time
import sqlite3
from pathlib import Path
from prompt_model import prompt_model

DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_DB_PATH = "data/jobs.db"

def get_rate_limits(model_name: str):
    rpm = 15
    tpm = 250000
    rpd = 500

    try:
        limits_file = Path("rate_limits.txt")
        if limits_file.exists():
            with limits_file.open("r") as f:
                for line in f:
                    parts = line.strip().split()
                    if parts and parts[0] == model_name:
                        rpm = int(parts[1])
                        tpm_str = parts[2].lower()
                        if tpm_str.endswith("k"):
                            tpm = int(tpm_str[:-1]) * 1000
                        else:
                            tpm = int(tpm_str)
                        rpd = int(parts[3])
                        break
    except Exception:
        print("Error: rate_limits.txt not found or invalid format. Using default values")
        pass
    return rpm, tpm, rpd

def get_db_connection(db_url: str):
    if not Path(db_url).exists():
        print(f"[Error] Database file does not exist at: {db_url}")
        sys.exit(1)
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
    if not cursor.fetchone():
        print("[Error] Table 'jobs' does not exist in the database.")
        conn.close()
        sys.exit(1)
    return conn

def fetch_untagged_jobs(cursor):
    cursor.execute("SELECT source_id, job_title, company, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''")
    return cursor.fetchall()

def process_job_description(model_name: str, job_title: str, company: str, description: str, source_id_str: str, retry_duration: float) -> str:
    prompt = (
        "You are an expert data labeling assistant. Analyze the following job description "
        "and extract the technical stack used in this job.\n"
        "Include programming languages, frameworks, libraries, databases, tools, APIs, cloud platforms, "
        "and methodologies (e.g., A/B testing, CI/CD, code reviews, testing, databases, APIs) "
        "that are explicitly required.\n\n"
        "You MUST output the result ONLY as a single line containing a comma-separated list of the technical stack, "
        "for example: \"Java, ABAP, enterprise systems, APIs, databases\".\n"
        "Do not include any introductory/concluding text, markdown, or formatting.\n\n"
        f"Job Title: {job_title}\n"
        f"Company: {company}\n"
        f"Description:\n{description}" # TODO: work on better prompt
    )
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            response = prompt_model(model_name, prompt)
            
            if "[Gemini Error]" in response or "[Ollama Error]" in response:
                print(f"[Job {source_id_str}] Attempt {attempt} failed: {response.strip()}")
            else:
                tech_stack = response.strip()
                if tech_stack.startswith('"') and tech_stack.endswith('"'):
                    tech_stack = tech_stack[1:-1].strip()
                elif tech_stack.startswith("'") and tech_stack.endswith("'"):
                    tech_stack = tech_stack[1:-1].strip()
                
                tech_stack = tech_stack.rstrip('.')
                return tech_stack
        except Exception as e:
            print(f"[Job {source_id_str}] Attempt {attempt} failed: {str(e)}")
        
        if attempt < max_attempts:
            time.sleep(retry_duration)
    return ""

def update_jobs_batch(cursor, conn, batch_updates):
    if batch_updates:
        cursor.executemany(
            "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
            batch_updates
        )
        conn.commit()

def tag_data(db_url: str):
    conn = None
    try:
        conn = get_db_connection(db_url)
        cursor = conn.cursor()
        rows = fetch_untagged_jobs(cursor)
        total_items = len(rows)
        
        if total_items == 0:
            print("[INFO] No data to tag.")
            sys.exit(0)

        model_name = DEFAULT_MODEL
        rpm, tpm, rpd = get_rate_limits(model_name)

        request_interval = (60.0 / rpm) if rpm > 0 else 4.0
        request_interval = max(1.0, request_interval + 0.5)
        
        retry_duration = max(5.0, 2.0 * request_interval)
        
        min_batch_size = (total_items + rpd - 1) // rpd if rpd > 0 else 5
        batch_size = max(5, min_batch_size)
        batches = [rows[i:i + batch_size] for i in range(0, total_items, batch_size)]
        
        global_idx = 0
        for batch_idx, batch_rows in enumerate(batches):
            batch_updates = []
            
            for row in batch_rows:
                source_id, job_title, company, description = row
                source_id_str = str(source_id)
                
                tech_stack = process_job_description(
                    model_name, job_title, company, description, source_id_str, retry_duration
                )
                
                if tech_stack:
                    batch_updates.append((tech_stack, source_id))
                    print(f"Analyzed Job {source_id_str}: {tech_stack}")
                else:
                    print(f"[Error] Job {source_id_str} failed all 3 attempts.")
                
                if global_idx < total_items - 1:
                    time.sleep(request_interval)
                global_idx += 1
            
            update_jobs_batch(cursor, conn, batch_updates)
                
    except Exception as e:
        print(f"[Error] Failed to execute tag_data: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

if __name__ == "__main__":
    if len(sys.argv) > 3:
        print("usage: uv run python tag_data.py [database_path] [model]")
        sys.exit(1)
    if len(sys.argv) >= 2:
        DEFAULT_DB_PATH = sys.argv[1]
    if len(sys.argv) == 3:
        DEFAULT_MODEL = sys.argv[2]
    tag_data(DEFAULT_DB_PATH)
