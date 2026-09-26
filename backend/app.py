
from pathlib import Path
import re
import sqlite3

from fastapi import FastAPI, Query


# ============================================================
# App
# ============================================================

app = FastAPI(
    title="Wolf Demure Pidgin Dictionary",
    version="2.1"
)


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
# Corpus matching
# ============================================================

def get_examples(
    conn,
    term,
    limit=3
):

    """
    Find corpus examples using word boundaries.

    Prevents searches such as:
        tout -> without
        am   -> example

    Also supports multi-word phrases.
    """

    term = normalize(term)

    rows = conn.execute(
        """
        SELECT
            record_id,
            pidgin_text,
            pidgin_normalized,
            english_text,
            source

        FROM parallel_sentences

        ORDER BY id
        """
    ).fetchall()

    pattern = re.compile(
        rf"(?<!\w){re.escape(term)}(?!\w)",
        re.IGNORECASE
    )

    examples = []

    for row in rows:

        text = (
            row["pidgin_normalized"]
            or row["pidgin_text"]
            or ""
        )

        if pattern.search(text):

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


# ============================================================
# Build API result
# ============================================================

def build_results(
    conn,
    rows
):

    grouped = {}

    for row in rows:

        word_id = row["id"]

        if word_id not in grouped:

            variant_rows = conn.execute(
                """
                SELECT variant

                FROM variants

                WHERE word_id = ?

                ORDER BY variant
                """,
                (
                    word_id,
                )
            ).fetchall()

            grouped[word_id] = {

                "word":
                    row["word"],

                "entry_type":
                    row["entry_type"],

                "pronunciation": {

                    "ipa":
                        row["ipa"],

                    "phonetic":
                        row["phonetic"],

                    "audio":
                        row["audio"]
                },

                "variants": [
                    variant["variant"]
                    for variant in variant_rows
                ],

                "definitions": [],

                "examples": []
            }

        if row["definition"]:

            definition = {

                "part_of_speech":
                    row["part_of_speech"],

                "definition":
                    row["definition"],

                "source":
                    row["definition_source"]
            }

            if (
                definition
                not in
                grouped[word_id]["definitions"]
            ):

                grouped[
                    word_id
                ]["definitions"].append(
                    definition
                )

    # --------------------------------------------------------
    # Corpus examples
    # --------------------------------------------------------

    for result in grouped.values():

        result["examples"] = get_examples(
            conn,
            result["word"],
            limit=3
        )

    return list(
        grouped.values()
    )


# ============================================================
# Home
# ============================================================

@app.get("/")
def home():

    return {
        "message":
            "Wolf Demure API is running",

        "version":
            "2.1"
    }


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "database": DB_FILE.exists()
    }


# ============================================================
# Search
# ============================================================

@app.get("/search")
def search(
    word: str = Query(
        ...,
        min_length=1
    )
):

    query = normalize(word)

    conn = get_connection()


    # ========================================================
    # 1. Exact canonical word / phrase
    # ========================================================

    rows = conn.execute(
        """
        SELECT

            w.id,
            w.word,
            w.word_normalized,
            w.entry_type,

            w.ipa,
            w.phonetic,
            w.audio,

            d.part_of_speech,
            d.definition,
            d.position,

            d.source AS definition_source

        FROM words w

        LEFT JOIN definitions d
            ON w.id = d.word_id

        WHERE w.word_normalized = ?

        ORDER BY
            d.position
        """,
        (
            query,
        )
    ).fetchall()


    if rows:

        results = build_results(
            conn,
            rows
        )

        conn.close()

        return {
            "found": True,
            "match_type": "exact",
            "count": len(results),
            "results": results
        }


    # ========================================================
    # 2. Exact variant
    # ========================================================

    rows = conn.execute(
        """
        SELECT

            w.id,
            w.word,
            w.word_normalized,
            w.entry_type,

            w.ipa,
            w.phonetic,
            w.audio,

            d.part_of_speech,
            d.definition,
            d.position,

            d.source AS definition_source

        FROM variants v

        JOIN words w
            ON v.word_id = w.id

        LEFT JOIN definitions d
            ON w.id = d.word_id

        WHERE v.variant_normalized = ?

        ORDER BY
            d.position
        """,
        (
            query,
        )
    ).fetchall()


    if rows:

        results = build_results(
            conn,
            rows
        )

        conn.close()

        return {
            "found": True,
            "match_type": "variant",
            "count": len(results),
            "results": results
        }


    # ========================================================
    # 3. Pidgin partial term search
    # ========================================================

    rows = conn.execute(
        """
        SELECT

            w.id,
            w.word,
            w.word_normalized,
            w.entry_type,

            w.ipa,
            w.phonetic,
            w.audio,

            d.part_of_speech,
            d.definition,
            d.position,

            d.source AS definition_source

        FROM words w

        LEFT JOIN definitions d
            ON w.id = d.word_id

        WHERE w.word_normalized LIKE ?

        ORDER BY
            LENGTH(w.word_normalized),
            w.word,
            d.position

        LIMIT 100
        """,
        (
            f"{query}%",
        )
    ).fetchall()


    if rows:

        results = build_results(
            conn,
            rows
        )

        conn.close()

        return {
            "found": True,
            "match_type": "partial",
            "count": len(results),
            "results": results
        }


    # ========================================================
    # 4. English definition search
    # ========================================================

    rows = conn.execute(
        """
        SELECT

            w.id,
            w.word,
            w.word_normalized,
            w.entry_type,

            w.ipa,
            w.phonetic,
            w.audio,

            d.part_of_speech,
            d.definition,
            d.position,

            d.source AS definition_source

        FROM definitions d

        JOIN words w
            ON d.word_id = w.id

        WHERE LOWER(d.definition)
              LIKE ?

        ORDER BY
            w.word,
            d.position

        LIMIT 100
        """,
        (
            f"%{query}%",
        )
    ).fetchall()


    if rows:

        results = build_results(
            conn,
            rows
        )

        conn.close()

        return {
            "found": True,
            "match_type": "definition",
            "count": len(results),
            "results": results
        }


    # ========================================================
    # No result
    # ========================================================

    conn.close()

    return {
        "found": False,
        "match_type": None,
        "count": 0,
        "results": [],
        "message":
            f"No definition found for '{word}'"
    }


# ============================================================
# Statistics
# ============================================================

@app.get("/stats")
def stats():

    conn = get_connection()

    terms = conn.execute(
        """
        SELECT COUNT(*)
        FROM words
        """
    ).fetchone()[0]

    words = conn.execute(
        """
        SELECT COUNT(*)
        FROM words
        WHERE entry_type = 'word'
        """
    ).fetchone()[0]

    phrases = conn.execute(
        """
        SELECT COUNT(*)
        FROM words
        WHERE entry_type = 'phrase'
        """
    ).fetchone()[0]

    definitions = conn.execute(
        """
        SELECT COUNT(*)
        FROM definitions
        """
    ).fetchone()[0]

    variants = conn.execute(
        """
        SELECT COUNT(*)
        FROM variants
        """
    ).fetchone()[0]

    pronunciations = conn.execute(
        """
        SELECT COUNT(*)

        FROM words

        WHERE ipa IS NOT NULL
          AND TRIM(ipa) != ''
        """
    ).fetchone()[0]

    parallel_sentences = conn.execute(
        """
        SELECT COUNT(*)
        FROM parallel_sentences
        """
    ).fetchone()[0]

    conn.close()

    return {
        "terms": terms,
        "words": words,
        "phrases": phrases,
        "definitions": definitions,
        "variants": variants,
        "pronunciations": pronunciations,
        "parallel_sentences":
            parallel_sentences
    }


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()
