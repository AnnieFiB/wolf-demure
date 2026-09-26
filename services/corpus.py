
import re
import sqlite3
from pathlib import Path


# ============================================================
# Database
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "wolf_demure.db"
)


def get_connection():

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    return conn


def normalize(text):

    if not text:
        return ""

    return " ".join(
        text.lower().strip().split()
    )


# ============================================================
# Get examples
# ============================================================

def get_word_examples(
    word,
    limit=3
):

    term = normalize(word)

    if not term:
        return []

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # LIKE is used only to reduce the number of rows
        # Python regex then performs the real whole-word match.
        # ----------------------------------------------------

        rows = conn.execute(
            """
            SELECT
                record_id,
                pidgin_text,
                pidgin_normalized,
                english_text,
                source

            FROM parallel_sentences

            WHERE LOWER(pidgin_normalized)
                  LIKE ?

            ORDER BY id
            """,
            (
                f"%{term}%",
            )
        ).fetchall()


        # ----------------------------------------------------
        # Whole word / whole phrase boundary
        #
        # Prevents:
        #
        # tout -> witout
        # am   -> example
        #
        # but supports:
        #
        # wahala
        # bad belle
        # carry go
        # ----------------------------------------------------

        pattern = re.compile(
            rf"(?<!\w)"
            rf"{re.escape(term)}"
            rf"(?!\w)",
            re.IGNORECASE
        )


        examples = []

        for row in rows:

            text = (
                row["pidgin_normalized"]
                or row["pidgin_text"]
                or ""
            )

            if not pattern.search(text):
                continue

            examples.append({

                "record_id":
                    row["record_id"],

                "pidgin_text":
                    row["pidgin_text"],

                "english_text":
                    row["english_text"],

                "source":
                    row["source"]
            })

            if len(examples) >= limit:
                break


        return examples

    finally:

        conn.close()
