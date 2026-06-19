from email import policy
import sys
import email


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


def extract_html_payload(mhtml_file):
    with open(mhtml_file, "rb") as binary_file:
        msg = email.message_from_binary_file(binary_file, policy=policy.default)

    for part in msg.walk():
        if part.get_content_type() == "text/html":
            return part.get_content()

    return None


def process_mhtml_file(mhtml_file, output_dir):
    try:
        clean_html = extract_html_payload(mhtml_file)

        if clean_html:
            output_file = output_dir / f"{mhtml_file.stem}.html"
            with open(output_file, "w", encoding="utf-8") as html_file:
                html_file.write(clean_html)
                print(f"✅ Extracted: {mhtml_file.name}")
                return True
        print(f"⚠️ No HTML content found in: {mhtml_file.name}")
        return False
    except Exception as err:
        print(f"⚠️ Failed to process {mhtml_file.name}: {err}")
        return False


def ingest_all_mhtml(input_dir, output_dir):
    print("🥉 Bronze: Starting extraction...")

    if not is_valid_directory(input_dir):
        print("\n📊 Bronze Summary:")
        print("Total: 0 | Extracted: 0 | Failed: 0")
        return
    output_dir.mkdir(parents=True, exist_ok=True)

    total = extracted = failed = 0

    for mhtml_file in input_dir.glob("*.mhtml"):
        total += 1
        result = process_mhtml_file(mhtml_file, output_dir)

        if result:
            extracted += 1
        else:
            failed += 1

    print("\n📊 Bronze Summary:")
    print(f"Total: {total} | Extracted: {extracted} | Failed: {failed}")
