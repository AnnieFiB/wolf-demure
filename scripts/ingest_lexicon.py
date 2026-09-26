
import json
import sqlite3
from collections import Counter
from pathlib import Path

from datasets import load_dataset


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "wolf_demure.db"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "raw"
    / "lexicon"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "pidgin_english_lexicon.json"
)


# ============================================================
# Helpers
# ============================================================

def normalize(text):
    """
    Basic normalization for comparison.

    We deliberately keep this simple for now.
    """
    if not text:
        return ""

    return " ".join(
        text.lower().strip().split()
    )


def is_phrase(term):
    """
    A term containing whitespace is treated as a phrase.
    """
    return len(term.split()) > 1


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("=" * 60)
    print("WOLF DEMURE — PIDGIN LEXICON INGESTION")
    print("=" * 60)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Download Hugging Face dataset
    # --------------------------------------------------------

    print()
    print("Loading Hugging Face lexicon...")

    dataset = load_dataset(
        "prince4332/unfiltered-pidgin-english-lexicon"
    )

    print()
    print("Available splits:")
    print(dataset)

    # Use the first available split
    split_name = list(dataset.keys())[0]
    data = dataset[split_name]

    print()
    print(f"Using split: {split_name}")
    print(f"Rows:        {len(data)}")
    print(f"Columns:     {data.column_names}")

    # --------------------------------------------------------
    # Show first record
    # --------------------------------------------------------

    if len(data) > 0:

        print()
        print("First record:")
        print(data[0])

    # --------------------------------------------------------
    # Convert to regular Python records
    # --------------------------------------------------------

    records = [
        dict(row)
        for row in data
    ]

    # --------------------------------------------------------
    # Save raw dataset
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Read existing Wolf Demure vocabulary
    # --------------------------------------------------------

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    existing_word_rows = conn.execute(
        """
        SELECT word_normalized
        FROM words
        """
    ).fetchall()

    existing_words = {
        normalize(row["word_normalized"])
        for row in existing_word_rows
    }

    existing_variant_rows = conn.execute(
        """
        SELECT variant
        FROM variants
        """
    ).fetchall()

    existing_variants = {
        normalize(row["variant"])
        for row in existing_variant_rows
    }

    conn.close()

    known_terms = (
        existing_words
        | existing_variants
    )

    # --------------------------------------------------------
    # Inspect lexicon
    # --------------------------------------------------------

    valid_records = []
    empty_records = []

    terms = []

    for index, record in enumerate(
        records,
        start=1
    ):

        # Expected dataset columns:
        # term
        # meaning

        term = normalize(
            record.get("term")
        )

        meaning = (
            record.get("meaning")
            or ""
        ).strip()

        # ---------------------------------------------
        # Empty/bad rows
        # ---------------------------------------------

        if not term or not meaning:

            empty_records.append({
                "row": index,
                "term": term,
                "meaning": meaning
            })

            continue

        valid_records.append({
            "term": term,
            "meaning": meaning
        })

        terms.append(term)

    # --------------------------------------------------------
    # Duplicate terms inside HF dataset
    # --------------------------------------------------------

    term_counts = Counter(terms)

    duplicate_terms = {
        term: count
        for term, count in term_counts.items()
        if count > 1
    }

    # --------------------------------------------------------
    # Compare with existing dictionary
    # --------------------------------------------------------

    exact_matches = set()
    new_words = set()
    new_phrases = set()

    for term in set(terms):

        if term in known_terms:

            exact_matches.add(term)

        elif is_phrase(term):

            new_phrases.add(term)

        else:

            new_words.add(term)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("LEXICON ANALYSIS COMPLETE")
    print("=" * 60)

    print(f"Raw HF rows:           {len(records)}")
    print(f"Valid records:         {len(valid_records)}")
    print(f"Empty/bad records:     {len(empty_records)}")

    print()

    print(f"Unique HF terms:       {len(set(terms))}")
    print(f"Duplicate terms:       {len(duplicate_terms)}")

    print()

    print(f"Existing dictionary:   {len(existing_words)}")
    print(f"Existing variants:     {len(existing_variants)}")
    print(f"Exact matches:         {len(exact_matches)}")
    print(f"New single words:      {len(new_words)}")
    print(f"New phrases:           {len(new_phrases)}")

    print()

    print(f"Saved to: {OUTPUT_FILE}")

    # --------------------------------------------------------
    # Show some matches
    # --------------------------------------------------------

    if exact_matches:

        print()
        print("EXAMPLE EXISTING MATCHES")
        print("-" * 60)

        for term in sorted(
            exact_matches
        )[:20]:

            print(term)

    # --------------------------------------------------------
    # Show new words
    # --------------------------------------------------------

    if new_words:

        print()
        print("FIRST 30 NEW WORDS")
        print("-" * 60)

        for term in sorted(
            new_words
        )[:30]:

            print(term)

    # --------------------------------------------------------
    # Show new phrases
    # --------------------------------------------------------

    if new_phrases:

        print()
        print("FIRST 30 NEW PHRASES")
        print("-" * 60)

        for term in sorted(
            new_phrases
        )[:30]:

            print(term)

    # --------------------------------------------------------
    # Show duplicates
    # --------------------------------------------------------

    if duplicate_terms:

        print()
        print("DUPLICATE TERMS")
        print("-" * 60)

        for term, count in sorted(
            duplicate_terms.items()
        )[:30]:

            print(
                f"{term:<35} {count}"
            )

    # --------------------------------------------------------
    # Show bad records
    # --------------------------------------------------------

    if empty_records:

        print()
        print("EMPTY / BAD RECORDS")
        print("-" * 60)

        for record in empty_records[:20]:

            print(record)


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()
