import sys
import sqlite3


def is_valid_database(db_path) -> bool:
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}", file=sys.stderr)
        return False
    if not db_path.is_file():
        print(f"❌ Path '{db_path}' exists but is not a file.", file=sys.stderr)
        return False
    return True


def fetch_metrics(cursor) -> dict:
    cursor.execute("""
        SELECT 
            COUNT(*),
            SUM(CASE WHEN job_title IS NULL THEN 1 ELSE 0 END),
            SUM(CASE WHEN company IS NULL THEN 1 ELSE 0 END),
            SUM(CASE WHEN description IS NULL THEN 1 ELSE 0 END),
            CAST(AVG(LENGTH(description)) AS INTEGER)
        FROM jobs
    """)
    total, null_title, null_company, null_desc, avg_desc = cursor.fetchone()

    if total == 0:
        return {"total": 0}

    cursor.execute("""
        SELECT LENGTH(description), source_id, job_title 
        FROM jobs 
        WHERE description IS NOT NULL
        ORDER BY LENGTH(description) ASC 
        LIMIT 1
    """)
    shortest = cursor.fetchone()

    cursor.execute("""
        SELECT LENGTH(description), source_id, job_title 
        FROM jobs 
        WHERE description IS NOT NULL
        ORDER BY LENGTH(description) DESC 
        LIMIT 1
    """)
    longest = cursor.fetchone()

    return {
        "total": total,
        "null_title": null_title or 0,
        "null_company": null_company or 0,
        "null_desc": null_desc or 0,
        "avg_desc": avg_desc or 0,
        "shortest": shortest,
        "longest": longest,
    }


def print_report(metrics):
    print("\n--- 🔍 DATA QUALITY REPORT ---")

    if metrics.get("total") == 0:
        print("📉 Database is empty. No metrics to report.")
        return

    print(f"📈 Total Records: {metrics['total']}")
    print(
        f"❓ Missing Values -> job_title: {metrics['null_title']}, company: {metrics['null_company']}, description: {metrics['null_desc']}"
    )
    print(f"📝 Avg Description Length: {metrics['avg_desc']} chars")

    shortest = metrics.get("shortest")
    if shortest:
        print(f"⚠️ Shortest Description: {shortest[0]} chars")
        print(f"   ↳ source_id: {shortest[1]} | job_title: {shortest[2]}")

    longest = metrics.get("longest")
    if longest:
        print(f"🚨 Longest Description: {longest[0]} chars")
        print(f"   ↳ source_id: {longest[1]} | job_title: {longest[2]}")


def run_data_profile(db_path):
    print("\n📊 Profiler: Analyzing Database metrics...")

    if not is_valid_database(db_path):
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        metrics = fetch_metrics(cursor)
        print_report(metrics)
        return True
    except sqlite3.Error as e:
        print(f"⚠️ Database Init error: {e}")
        return False
    finally:
        if "conn" in locals():
            conn.close()
