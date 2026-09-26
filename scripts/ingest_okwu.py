
import json
from pathlib import Path

from datasets import load_dataset


BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "raw"
    / "okwu"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "pidgin_english.json"
)


def main():

    print("=" * 60)
    print("WOLF DEMURE — OKWU INGESTION")
    print("=" * 60)

    print("Loading Okwu dataset...")

    dataset = load_dataset(
        "Okwu/african-language-parallel-corpus",
        "pcm-eng"
    )

    print(dataset)

    # We'll inspect the structure before doing
    # any transformation.
    split_name = list(dataset.keys())[0]

    data = dataset[split_name]

    print()
    print(f"Using split: {split_name}")
    print(f"Rows: {len(data)}")

    print()
    print("Columns:")
    print(data.column_names)

    print()
    print("First record:")
    print(data[0])

    # Create raw directory
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save the raw records for inspection
    records = [
        dict(row)
        for row in data
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    print(f"Rows saved: {len(records)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
