
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path


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

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "vocabulary_candidates.json"
)


# ============================================================
# Tokenizer
# ============================================================

def tokenize(text):

    """
    Simple tokenizer for vocabulary discovery.

    Keeps alphabetic words and apostrophes.
    Converts everything to lowercase.
    """

    text = text.lower()

    return re.findall(
        r"[a-zÀ-ÖØ-öø-ÿ]+(?:'[a-zÀ-ÖØ-öø-ÿ]+)?",
        text
    )


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("=" * 60)
    print("WOLF DEMURE — VOCABULARY DISCOVERY")
    print("=" * 60)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    # --------------------------------------------------------
    # Existing dictionary words
    # --------------------------------------------------------

    word_rows = conn.execute(
        """
        SELECT word_normalized
        FROM words
        """
    ).fetchall()

    existing_words = {
        row["word_normalized"].lower().strip()
        for row in word_rows
    }

    # --------------------------------------------------------
    # Existing variants
    # --------------------------------------------------------

    variant_rows = conn.execute(
        """
        SELECT variant
        FROM variants
        """
    ).fetchall()

    existing_variants = {
        row["variant"].lower().strip()
        for row in variant_rows
    }

    known_vocabulary = (
        existing_words
        | existing_variants
    )

    # --------------------------------------------------------
    # Okwu corpus
    # --------------------------------------------------------

    sentences = conn.execute(
        """
        SELECT
            record_id,
            pidgin_normalized
        FROM parallel_sentences
        """
    ).fetchall()

    conn.close()

    print(f"Dictionary words:     {len(existing_words)}")
    print(f"Known variants:       {len(existing_variants)}")
    print(f"Corpus sentences:     {len(sentences)}")

    # --------------------------------------------------------
    # Count tokens
    # --------------------------------------------------------

    token_counts = Counter()

    # Keep example sentences for each token
    examples = {}

    total_tokens = 0

    for row in sentences:

        sentence = row["pidgin_normalized"]

        tokens = tokenize(sentence)

        total_tokens += len(tokens)

        token_counts.update(tokens)

        # Save up to 3 example sentences
        for token in set(tokens):

            if token not in examples:
                examples[token] = []

            if len(examples[token]) < 3:

                examples[token].append({
                    "record_id": row["record_id"],
                    "sentence": sentence
                })

    # --------------------------------------------------------
    # Find unknown vocabulary
    # --------------------------------------------------------

    candidates = []

    for token, frequency in token_counts.most_common():

        # Already in dictionary
        if token in known_vocabulary:
            continue

        # Ignore single-character noise
        if len(token) < 2:
            continue

        candidates.append({
            "word": token,
            "frequency": frequency,
            "examples": examples.get(
                token,
                []
            )
        })

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            candidates,
            file,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("DISCOVERY COMPLETE")
    print("=" * 60)

    print(f"Total corpus tokens:  {total_tokens}")
    print(f"Unique tokens:        {len(token_counts)}")
    print(f"Known vocabulary:     {len(known_vocabulary)}")
    print(f"New candidates:       {len(candidates)}")

    print()
    print("TOP 50 UNKNOWN TOKENS")
    print("-" * 60)

    for candidate in candidates[:50]:

        print(
            f"{candidate['word']:<20}"
            f"{candidate['frequency']:>6}"
        )

    print()
    print(f"Saved to: {OUTPUT_FILE}")


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()
