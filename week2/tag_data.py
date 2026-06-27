import sys
import json
import sqlite3
from pathlib import Path
from prompt_model import prompt_model

DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_DB_PATH = "data/jobs_d1.db"

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

def process_job_batch(model_name: str, batch_rows: list) -> dict[str, str]:
    jobs_text = ""
    for source_id, description in batch_rows:
        jobs_text += f"--- JOB ID: {source_id} ---\n{description}\n\n"
        
    prompt = (
        "You are an expert data labeling assistant. Analyze the following batch of job descriptions "
        "and extract the technical stack explicitly required for each job.\n\n"
        "### EXTRACTION RULES:\n"
        "1. Include: programming languages, frameworks, libraries, databases, tools, cloud platforms, APIs, "
        "and technical methodologies (e.g., CI/CD, Agile, A/B testing, TDD).\n"
        "2. Strict Grounding: Only extract skills explicitly written in the text. Do NOT infer skills.\n"
        '3. The Empty Rule: If a job description contains zero technical skills, its value MUST be an empty string "".\n'
        "4. Key Preservation: Your output JSON must contain an exact key for EVERY Job ID provided in the input, even if empty.\n\n"
        "### OUTPUT FORMAT:\n"
        "Respond with ONLY a valid, raw JSON object. Do not wrap it in ```json markdown fences.\n"
        "Example output:\n"
        "{\n"
        '  "91234": "Java, Spring Boot, MySQL",\n'
        '  "95678": "Python, Django, PostgreSQL",\n'
        '  "99999": ""\n'
        "}\n\n"
        "### INPUT DATA:\n"
        f"{jobs_text}"
    )
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            response = prompt_model(model_name, prompt)
            if "[Gemini Error]" in response or "[Ollama Error]" in response:
                print(f"[Batch Attempt {attempt}] failed: {response.strip()}")
                sys.exit(1)
            
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            data = json.loads(clean_response)
            return {str(k).strip(): str(v).strip() for k, v in data.items()}
        except Exception as e:
            print(f"[Batch Attempt {attempt}] failed to parse/call: {str(e)}")
    return {}

def update_jobs_batch(conn, batch_updates):
    if batch_updates:
        conn.cursor().executemany(
            "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
            batch_updates
        )
        conn.commit()

def tag_data(db_url: str):
    if not Path(db_url).exists():
        print(f"[Error] Database file does not exist at: {db_url}")
        sys.exit(1)
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''")
        rows = cursor.fetchall()
        total_items = len(rows)
        
        if total_items == 0:
            print("[INFO] No data to tag.")
            sys.exit(0)

        model_name = DEFAULT_MODEL
        rpm, tpm, rpd = get_rate_limits(model_name)

        min_batch_size = (total_items + rpd - 1) // rpd if rpd > 0 else 5
        batch_size = max(5, min_batch_size)
        batches = [rows[i:i + batch_size] for i in range(0, total_items, batch_size)]
        
        for batch_idx, batch_rows in enumerate(batches):
            batch_updates = []
            
            print(f"[Batch {batch_idx}] Requesting LLM for {len(batch_rows)} jobs...")
            batch_results = process_job_batch(model_name, batch_rows)
            
            for row in batch_rows:
                source_id, description = row
                source_id_str = str(source_id)
                
                tech_stack = batch_results.get(source_id_str, None)
                if tech_stack is not None:
                    db_value = "N/A" if tech_stack.strip() == "" else tech_stack
                    batch_updates.append((db_value, source_id))
                    print(f"[Batch {batch_idx}] Analyzed Job {source_id_str}: {db_value}")
                else:
                    print(f"[Error] Job {source_id_str} not found in batch results or failed.")
            update_jobs_batch(conn, batch_updates)
            batch_updates.clear()
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
