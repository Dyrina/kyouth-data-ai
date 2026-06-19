# Week 1: Data Input & Processing Component

## Project Description
An automated Data Engineering pipeline that extracts raw job postings from the web, cleans and structures the data, and stores it in a relational database. 

Built using the industry-standard Medallion Architecture, this project guarantees data quality, prevents duplicate records via idempotency, and transforms messy web data into a reliable, business-ready "Single Source of Truth."

## Architecture (ETL & Medallion)

This pipeline processes data through three progressive stages of quality:

- Bronze Layer (Ingestion): Extracts raw .mhtml page archives into readable .html files. The data is kept in its raw, messy state to preserve an immutable history of the extraction.
- Silver Layer (Processing): Uses BeautifulSoup to parse HTML tags and extract key entities (Job Title, Company, Description). Pydantic models act as strict data contracts, validating types and dropping incomplete records before saving them as clean JSON files.
- Gold Layer (Data Warehouse): Loads the validated JSON files into an SQLite database. It utilizes INSERT OR IGNORE SQL logic with strict Primary Keys (source_id) to ensure the pipeline is completely idempotent, preventing duplicate entries across multiple runs.

## Setup
- Ensure you have `uv` installed on your system. If not, install it from [here](https://docs.astral.sh/uv/#installation)
1. `git clone` this repository
2. Run `uv sync` for the first to download the dependencies
3. Create a `data/` directory and add the `0_source` directory in it. (If you don't have it, download it from [Day 1](https://fxdigitalskills.notion.site/Day-1-Extractor-Bronze-Layer-35117c3c3ec080d5bee7d5f87355cbcd) in notion)
4. Then you can run the program using `uv`.
	- `uv run python main.py [ingest|process|load|profile|all]`

## Technical Reflections

### Day 1: The Extractor (Medallion & Lakehouses)
Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?

- **Answer**: Keeping raw HTML in the Bronze layer acts as an immutable time capsule. By preserving the exact state of the original webpage, you prevent permanent data loss. If business needs change—like deciding to track salary ranges later—you can simply update your parser and extract that new data from the saved files instead of losing months of history.

	Additionally, it guarantees replayability for safe debugging. If a bug ever corrupts your database, you don't need to re-scrape the website (which might have already deleted the job post). You just fix your code and safely rerun the pipeline from the original Bronze data.

### Day 2: Treatment Plant (ETL vs ELT & Scale)
Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?
- **Answer**: Cloud platforms prefer **ELT** (Extract, Load, Transform) because modern cloud databases have massive storage and powerful compute engines. Loading raw data immediately removes processing bottlenecks, allowing the warehouse to quickly clean the data natively using highly scalable SQL.

	Additionally, processing files sequentially (one by one) is too slow for massive datasets. Distributed processing tools like Apache Spark solve this by splitting the workload across hundreds of servers simultaneously, turning days of sequential processing into just a few minutes.

### Day 3: The Blueprint & The Vault (Storage & Contracts)
What should happen if an important field like job_title disappears? Why fail early instead of silently inserting nulls into DB? How does INSERT OR IGNORE help prevent duplicate records?
- **Answer**: If a critical field like `job_title` goes missing, the pipeline must reject the record immediately. Failing early using strict Data Contracts (like Pydantic) prevents silent `NULL` values from sneaking into your Data Warehouse and breaking downstream business dashboards. It is always safer to drop a bad record at the gate than to permanently pollute your company's "single source of truth."

	Additionally, using `INSERT OR IGNORE` guarantees your pipeline is idempotent. By checking a strict Primary Key (like `source_id`), the database automatically skips records it has already saved instead of crashing or creating duplicates. This ensures that no matter how many times your pipeline runs or fails, your database remains perfectly accurate.

### Day 4: The QA Inspector & Orchestrator (Orchestration & DAGs)
What happens if processor.py crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?
- **Answer**: Manually running scripts is risky: if a process crashes halfway, engineers must dig through logs to safely restart it without duplicating data. Automated orchestrators like Airflow solve this by tracking every single step. If a failure occurs, they pause, alert you, and can automatically resume exactly where they left off once the issue is fixed.