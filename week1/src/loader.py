import sys
import json
import sqlite3


def is_valid_directory(directory_path) -> bool:
    if not directory_path.exists():
        print(
            f"\nError: The source directory '{directory_path}' does not exist.",
            file=sys.stderr,
        )
        return False
    if not directory_path.is_dir():
        print(
            f"\nError: '{directory_path}' exists, but it is a file, not a directory.",
            file=sys.stderr,
        )
        return False
    return True


def insert_json(json_file, cursor) -> bool:
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        cursor.execute(
            """
            INSERT OR IGNORE INTO jobs (source_id, job_title, company, description, tech_stack)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                data.get("source_id"),
                data.get("job_title"),
                data.get("company"),
                data.get("description"),
                None,
            ),
        )
        was_inserted = cursor.rowcount > 0
        if was_inserted:
            print(f"✅ Inserted: {json_file.name}")
            return True
        else:
            print(f"⏭️ Skipped (duplicate): {json_file.name}")
            return False
    except Exception as e:
        print(f"⚠️ Failed to load {json_file.name}: {e}")
        return False


def load_all_jsons(input_dir, output_dir):
    print("🥇 Gold: Reading JSON files and populating the database...")

    if not is_valid_directory(input_dir):
        print("\n📊 Gold Summary:")
        print("Total: 0 | Inserted: 0 | Skipped: 0")
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "jobs.db"

    total = inserted = skipped = 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                source_id TEXT PRIMARY KEY,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                description TEXT NOT NULL,
                tech_stack TEXT
            )
        """)
        conn.commit()
        for json_file in input_dir.glob("*.json"):
            total += 1
            result = insert_json(json_file, cursor)
            if result:
                inserted += 1
            else:
                skipped += 1
        cursor.connection.commit()
    except sqlite3.Error as db_error:
        print(f"⚠️ Database Init error: {db_error}")
    finally:
        if "conn" in locals():
            conn.close()

    print("\n📊 Gold Summary:")
    print(f"Total: {total} | Inserted: {inserted} | Skipped: {skipped}")
