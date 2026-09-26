
import json
import sqlite3
from pathlib import Path


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

WIKTIONARY_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "wiktionary"
    / "pidgin_enriched.json"
)

LEXICON_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "lexicon"
    / "pidgin_english_lexicon.json"
)

OKWU_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "okwu"
    / "pidgin_english.json"
)

DB_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "wolf_demure.db"
)


# ============================================================
# Helpers
# ============================================================

def normalize(text):
    """
    Normalize terms for matching.

    Keeps punctuation and spelling intact,
    but standardizes case and whitespace.
    """

    if not text:
        return ""

    return " ".join(
        text.lower().strip().split()
    )


def get_entry_type(term):
    """
    Basic initial classification.

    Single token  -> word
    Multiple      -> phrase

    We can introduce slang, expression,
    abbreviation, cultural_term, etc. later.
    """

    if len(term.split()) > 1:
        return "phrase"

    return "word"


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("=" * 60)
    print("WOLF DEMURE — DATABASE BUILD")
    print("=" * 60)

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    DB_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load Wiktionary
    # --------------------------------------------------------

    with open(
        WIKTIONARY_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        wiktionary_records = json.load(file)

    # --------------------------------------------------------
    # Load HF lexicon
    # --------------------------------------------------------

    with open(
        LEXICON_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        lexicon_records = json.load(file)

    # --------------------------------------------------------
    # Load Okwu
    # --------------------------------------------------------

    with open(
        OKWU_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        okwu_records = json.load(file)

    # --------------------------------------------------------
    # Rebuild database
    # --------------------------------------------------------

    if DB_FILE.exists():
        DB_FILE.unlink()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "PRAGMA foreign_keys = ON"
    )


    # ========================================================
    # Create tables
    # ========================================================

    cursor.executescript(
        """
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            word TEXT NOT NULL,
            word_normalized TEXT NOT NULL UNIQUE,

            entry_type TEXT NOT NULL DEFAULT 'word',

            ipa TEXT,
            phonetic TEXT,
            audio TEXT,

            source TEXT,
            source_page_id INTEGER
        );


        CREATE TABLE definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            word_id INTEGER NOT NULL,

            part_of_speech TEXT,
            definition TEXT NOT NULL,

            position INTEGER,

            source TEXT,
            source_record_id TEXT,

            FOREIGN KEY (word_id)
                REFERENCES words(id)
                ON DELETE CASCADE
        );


        CREATE TABLE variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            word_id INTEGER NOT NULL,

            variant TEXT NOT NULL,
            variant_normalized TEXT NOT NULL,

            FOREIGN KEY (word_id)
                REFERENCES words(id)
                ON DELETE CASCADE
        );


        CREATE TABLE parallel_sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            record_id TEXT UNIQUE NOT NULL,

            pidgin_text TEXT NOT NULL,
            pidgin_normalized TEXT NOT NULL,

            english_text TEXT NOT NULL,

            verified INTEGER NOT NULL,

            source TEXT,
            source_url TEXT
        );


        CREATE INDEX idx_words_normalized
        ON words(word_normalized);


        CREATE INDEX idx_words_entry_type
        ON words(entry_type);


        CREATE INDEX idx_definitions_word_id
        ON definitions(word_id);


        CREATE INDEX idx_definitions_source
        ON definitions(source);


        CREATE INDEX idx_variants_word_id
        ON variants(word_id);


        CREATE INDEX idx_variants_normalized
        ON variants(variant_normalized);


        CREATE INDEX idx_parallel_pidgin
        ON parallel_sentences(pidgin_normalized);


        CREATE INDEX idx_parallel_english
        ON parallel_sentences(english_text);
        """
    )


    # ========================================================
    # Track canonical terms
    # ========================================================

    word_ids = {}


    # ========================================================
    # 1. Insert Wiktionary
    # ========================================================

    print()
    print("Loading Wiktionary...")

    for record in wiktionary_records:

        word = (
            record.get("pidgin")
            or ""
        ).strip()

        word_normalized = normalize(word)

        if not word_normalized:
            continue

        pronunciation = (
            record.get("pronunciation")
            or {}
        )

        # ----------------------------------------------------
        # Insert canonical word
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO words (
                word,
                word_normalized,
                entry_type,
                ipa,
                phonetic,
                audio,
                source,
                source_page_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                word,
                word_normalized,
                get_entry_type(word),
                pronunciation.get("ipa"),
                pronunciation.get("phonetic"),
                pronunciation.get("audio"),
                "Wiktionary",
                record.get("pageid")
            )
        )

        word_id = cursor.lastrowid

        word_ids[word_normalized] = word_id


        # ----------------------------------------------------
        # Wiktionary definitions
        # ----------------------------------------------------

        position = 1

        for entry in record.get(
            "entries",
            []
        ):

            part_of_speech = (
                entry.get("part_of_speech")
            )

            for definition in entry.get(
                "definitions",
                []
            ):

                definition = (
                    definition
                    or ""
                ).strip()

                if not definition:
                    continue

                cursor.execute(
                    """
                    INSERT INTO definitions (
                        word_id,
                        part_of_speech,
                        definition,
                        position,
                        source,
                        source_record_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        word_id,
                        part_of_speech,
                        definition,
                        position,
                        "Wiktionary",
                        str(record.get("pageid"))
                        if record.get("pageid") is not None
                        else None
                    )
                )

                position += 1


        # ----------------------------------------------------
        # Wiktionary variants
        # ----------------------------------------------------

        for variant in record.get(
            "variants",
            []
        ):

            variant = (
                variant
                or ""
            ).strip()

            variant_normalized = normalize(
                variant
            )

            if not variant_normalized:
                continue

            cursor.execute(
                """
                INSERT INTO variants (
                    word_id,
                    variant,
                    variant_normalized
                )
                VALUES (?, ?, ?)
                """,
                (
                    word_id,
                    variant,
                    variant_normalized
                )
            )


    # ========================================================
    # 2. Insert HF Pidgin-English Lexicon
    # ========================================================

    print("Loading HF Pidgin-English Lexicon...")

    lexicon_valid = 0
    lexicon_skipped = 0
    lexicon_new_terms = 0
    lexicon_existing_terms = 0
    lexicon_definitions_added = 0

    for row_number, record in enumerate(
        lexicon_records,
        start=1
    ):

        term = (
            record.get("term")
            or ""
        ).strip()

        meaning = (
            record.get("meaning")
            or ""
        ).strip()

        term_normalized = normalize(term)

        # ----------------------------------------------------
        # Skip incomplete rows
        # ----------------------------------------------------

        if not term_normalized or not meaning:

            lexicon_skipped += 1
            continue

        lexicon_valid += 1


        # ----------------------------------------------------
        # Existing canonical term
        # ----------------------------------------------------

        if term_normalized in word_ids:

            word_id = word_ids[
                term_normalized
            ]

            lexicon_existing_terms += 1


        # ----------------------------------------------------
        # New canonical term
        # ----------------------------------------------------

        else:

            cursor.execute(
                """
                INSERT INTO words (
                    word,
                    word_normalized,
                    entry_type,
                    source
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    term,
                    term_normalized,
                    get_entry_type(term),
                    "HF Pidgin-English Lexicon"
                )
            )

            word_id = cursor.lastrowid

            word_ids[
                term_normalized
            ] = word_id

            lexicon_new_terms += 1


        # ----------------------------------------------------
        # Avoid exact duplicate definitions
        # ----------------------------------------------------

        existing_definition = cursor.execute(
            """
            SELECT 1
            FROM definitions

            WHERE word_id = ?
              AND LOWER(TRIM(definition))
                  = LOWER(TRIM(?))

            LIMIT 1
            """,
            (
                word_id,
                meaning
            )
        ).fetchone()


        if existing_definition:
            continue


        # ----------------------------------------------------
        # Add lexicon definition
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                COALESCE(MAX(position), 0) + 1

            FROM definitions

            WHERE word_id = ?
            """,
            (
                word_id,
            )
        )

        position = cursor.fetchone()[0]


        cursor.execute(
            """
            INSERT INTO definitions (
                word_id,
                part_of_speech,
                definition,
                position,
                source,
                source_record_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                word_id,
                None,
                meaning,
                position,
                "HF Pidgin-English Lexicon",
                str(row_number)
            )
        )

        lexicon_definitions_added += 1


    # ========================================================
    # 3. Insert Okwu parallel sentences
    # ========================================================

    print("Loading Okwu corpus...")

    okwu_skipped = 0

    for record in okwu_records:

        pidgin_normalized = (
            record.get(
                "source_text_normalized"
            )
            or record.get(
                "source_text"
            )
            or ""
        ).strip()

        pidgin_text = (
            record.get("source_text")
            or pidgin_normalized
        ).strip()

        english = (
            record.get(
                "english_translation"
            )
            or ""
        ).strip()


        # ----------------------------------------------------
        # Skip incomplete records
        # ----------------------------------------------------

        if (
            not pidgin_normalized
            or not english
        ):

            okwu_skipped += 1
            continue


        # ----------------------------------------------------
        # Skip known junk/header record
        # ----------------------------------------------------

        if (
            pidgin_normalized.lower()
            in {"pidgin", "pdgin"}
            and
            english.lower() == "english"
        ):

            okwu_skipped += 1
            continue


        # ----------------------------------------------------
        # Insert corpus record
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO parallel_sentences (
                record_id,
                pidgin_text,
                pidgin_normalized,
                english_text,
                verified,
                source,
                source_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["record_id"],
                pidgin_text,
                pidgin_normalized,
                english,
                int(
                    record.get(
                        "verified",
                        False
                    )
                ),
                record.get("source"),
                record.get("source_url")
            )
        )


    # ========================================================
    # Commit
    # ========================================================

    conn.commit()


    # ========================================================
    # Validation counts
    # ========================================================

    word_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM words
        """
    ).fetchone()[0]


    single_word_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM words
        WHERE entry_type = 'word'
        """
    ).fetchone()[0]


    phrase_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM words
        WHERE entry_type = 'phrase'
        """
    ).fetchone()[0]


    definition_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM definitions
        """
    ).fetchone()[0]


    wiktionary_definition_count = (
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM definitions
            WHERE source = 'Wiktionary'
            """
        ).fetchone()[0]
    )


    lexicon_definition_count = (
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM definitions
            WHERE source =
                'HF Pidgin-English Lexicon'
            """
        ).fetchone()[0]
    )


    variant_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM variants
        """
    ).fetchone()[0]


    pronunciation_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM words

        WHERE ipa IS NOT NULL
          AND TRIM(ipa) != ''
        """
    ).fetchone()[0]


    sentence_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM parallel_sentences
        """
    ).fetchone()[0]


    verified_sentence_count = (
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM parallel_sentences
            WHERE verified = 1
            """
        ).fetchone()[0]
    )


    conn.close()


    # ========================================================
    # Results
    # ========================================================

    print()
    print("=" * 60)
    print("DATABASE BUILD COMPLETE")
    print("=" * 60)

    print()
    print("DICTIONARY")
    print("-" * 60)

    print(
        f"Total terms:             "
        f"{word_count}"
    )

    print(
        f"Single words:            "
        f"{single_word_count}"
    )

    print(
        f"Phrases:                 "
        f"{phrase_count}"
    )

    print(
        f"Definitions:             "
        f"{definition_count}"
    )

    print(
        f"Wiktionary definitions: "
        f"{wiktionary_definition_count}"
    )

    print(
        f"Lexicon definitions:     "
        f"{lexicon_definition_count}"
    )

    print(
        f"Variants:                "
        f"{variant_count}"
    )

    print(
        f"With IPA:                "
        f"{pronunciation_count}"
    )


    print()
    print("HF LEXICON")
    print("-" * 60)

    print(
        f"Raw records:             "
        f"{len(lexicon_records)}"
    )

    print(
        f"Valid records:           "
        f"{lexicon_valid}"
    )

    print(
        f"Skipped records:         "
        f"{lexicon_skipped}"
    )

    print(
        f"Existing terms matched:  "
        f"{lexicon_existing_terms}"
    )

    print(
        f"New terms added:         "
        f"{lexicon_new_terms}"
    )

    print(
        f"Definitions added:       "
        f"{lexicon_definitions_added}"
    )


    print()
    print("OKWU CORPUS")
    print("-" * 60)

    print(
        f"Raw records:             "
        f"{len(okwu_records)}"
    )

    print(
        f"Skipped records:         "
        f"{okwu_skipped}"
    )

    print(
        f"Parallel sentences:      "
        f"{sentence_count}"
    )

    print(
        f"Verified sentences:      "
        f"{verified_sentence_count}"
    )


    print()
    print(
        f"Database: {DB_FILE}"
    )


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()
