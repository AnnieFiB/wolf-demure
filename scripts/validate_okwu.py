
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "okwu"
    / "pidgin_english.json"
)


def main():

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    missing_pidgin = []
    missing_english = []
    unverified = []
    duplicates = []
    suspicious = []

    seen = set()

    for record in records:

        record_id = record["record_id"]

        pidgin = (
            record.get("source_text_normalized")
            or record.get("source_text")
            or ""
        ).strip()

        english = (
            record.get("english_translation")
            or ""
        ).strip()

        # Missing values
        if not pidgin:
            missing_pidgin.append(record_id)

        if not english:
            missing_english.append(record_id)

        # Verification
        if not record.get("verified"):
            unverified.append(record_id)

        # Duplicate sentence pairs
        key = (
            pidgin.lower(),
            english.lower()
        )

        if key in seen:
            duplicates.append(
                (record_id, pidgin, english)
            )
        else:
            seen.add(key)

        # Obvious suspicious/header rows
        if (
            pidgin.lower() in {"pidgin", "pdgin"}
            and english.lower() == "english"
        ):
            suspicious.append(
                (record_id, pidgin, english)
            )

    print()
    print("=" * 55)
    print("WOLF DEMURE — OKWU VALIDATION")
    print("=" * 55)

    print(f"Total records:        {len(records)}")
    print(f"Missing Pidgin:       {len(missing_pidgin)}")
    print(f"Missing English:      {len(missing_english)}")
    print(f"Unverified:           {len(unverified)}")
    print(f"Duplicate pairs:      {len(duplicates)}")
    print(f"Suspicious records:   {len(suspicious)}")

    if suspicious:

        print()
        print("SUSPICIOUS RECORDS")
        print("-" * 55)

        for record_id, pidgin, english in suspicious:
            print(
                f"{record_id}: "
                f"{pidgin} -> {english}"
            )

    if duplicates:

        print()
        print("FIRST 10 DUPLICATES")
        print("-" * 55)

        for record_id, pidgin, english in duplicates[:10]:
            print(
                f"{record_id}: "
                f"{pidgin} -> {english}"
            )


if __name__ == "__main__":
    main()
