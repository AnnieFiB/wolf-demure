import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "wolf_demure.db"
)

def search_dictionary(query):

    query = query.lower().strip()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    # --------------------------------------------------------
    # First find matching word IDs
    # --------------------------------------------------------

    matching_words = conn.execute(
        """
        SELECT DISTINCT w.id
        FROM words w

        LEFT JOIN definitions d
            ON w.id = d.word_id

        LEFT JOIN variants v
            ON w.id = v.word_id

        WHERE
            -- Exact Pidgin word with a definition
            (
                w.word_normalized = ?
                AND d.definition IS NOT NULL
            )

            -- Variant spelling
            OR LOWER(v.variant) = ?

            -- Exact English definition
            OR LOWER(d.definition) = ?

            -- English meaning in comma-separated definitions
            OR LOWER(d.definition) LIKE ?
            OR LOWER(d.definition) LIKE ?
            OR LOWER(d.definition) LIKE ?

            -- English word inside a phrase
            OR LOWER(d.definition) LIKE ?
        """,
        (
            query,
            query,
            query,
            f"{query},%",
            f"%, {query},%",
            f"%, {query}",
            f"% {query}%"
        )
    ).fetchall()

    if not matching_words:
        conn.close()
        return []

    word_ids = [
        row["id"]
        for row in matching_words
    ]

    # --------------------------------------------------------
    # Now retrieve ALL definitions for matched words
    # --------------------------------------------------------

    placeholders = ",".join(
        "?" for _ in word_ids
    )

    results = conn.execute(
        f"""
        SELECT
            w.id,
            w.word,
            w.ipa,
            d.part_of_speech,
            d.definition
        FROM words w

        LEFT JOIN definitions d
            ON w.id = d.word_id

        WHERE w.id IN ({placeholders})

        ORDER BY
            w.word,
            d.position
        """,
        word_ids
    ).fetchall()

    conn.close()

    return results
