from pydantic import BaseModel, ValidationError, Field
from bs4 import BeautifulSoup
import sys


class JobListing(BaseModel):
    source_id: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    description: str = Field(min_length=1)


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


def process_html_file(html_file, output_dir) -> bool:
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        source_id = soup.find("meta", attrs={"property": "og:url"})
        source_id = source_id["content"].split("/")[-1] if source_id else None
        job_title = soup.find(attrs={"data-automation": "job-detail-title"})
        job_title = job_title.get_text(strip=True) if job_title else None
        company = soup.find(attrs={"data-automation": "advertiser-name"})
        company = company.get_text(strip=True) if company else None
        description = soup.find(attrs={"data-automation": "jobAdDetails"})
        description = description.get_text(" ", strip=True) if description else None
        try:
            job_listing = JobListing(
                source_id=source_id,
                job_title=job_title,
                company=company,
                description=description,
            )
        except ValidationError as e:
            for err in e.errors():
                field_name = str(err["loc"][0])
                print(f"⚠️ Missing {field_name} in: {html_file.name}")
            return False
        output_file = output_dir / f"{html_file.stem}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(job_listing.model_dump_json(indent=2))
        print(f"✅ Processed: {html_file.name}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to process {html_file.name}: {err}")
        return False


def process_all_html(input_dir, output_dir):
    print("🥈 Silver: Cleaning and structuring extracted data...")

    if not is_valid_directory(input_dir):
        print("\n📊 Silver Summary:")
        print("Total: 0 | Processed: 0 | Skipped: 0")
        return
    output_dir.mkdir(parents=True, exist_ok=True)

    total = processed = skipped = 0

    for html_file in input_dir.glob("*.html"):
        total += 1
        result = process_html_file(html_file, output_dir)

        if result:
            processed += 1
        else:
            skipped += 1

    print("\n📊 Silver Summary:")
    print(f"Total: {total} | Processed: {processed} | Skipped: {skipped}")
