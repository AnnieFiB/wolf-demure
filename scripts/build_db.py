
import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "wiktionary"
    / "pidgin_enriched.json"
)

DB_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "wolf_demure.db"
)


def main():

    # Make sure output directory exists
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load enriched Wiktionary data
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    # Rebuild database
    if DB_FILE.exists():
        DB_FILE.unlink()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # ----------------------------------------
    # Create tables
    # ----------------------------------------

    cursor.executescript("""
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            word_normalized TEXT NOT NULL,
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
            FOREIGN KEY (word_id)
                REFERENCES words(id)
        );

        CREATE TABLE variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            variant TEXT NOT NULL,
            FOREIGN KEY (word_id)
                REFERENCES words(id)
        );

        CREATE INDEX idx_words_normalized
        ON words(word_normalized);

        CREATE INDEX idx_definitions_word_id
        ON definitions(word_id);

        CREATE INDEX idx_variants_word_id
        ON variants(word_id);
    """)

    # ----------------------------------------
    # Insert records
    # ----------------------------------------

    for record in records:

        word = record["pidgin"]

        pronunciation = record.get(
            "pronunciation", {}
        )

        cursor.execute(
            """
            INSERT INTO words (
                word,
                word_normalized,
                ipa,
                phonetic,
                audio,
                source,
                source_page_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                word,
                word.lower().strip(),
                pronunciation.get("ipa"),
                pronunciation.get("phonetic"),
                pronunciation.get("audio"),
                record.get("source"),
                record.get("pageid")
            )
        )

        word_id = cursor.lastrowid

        # Definitions
        position = 1

        for entry in record.get("entries", []):

            part_of_speech = entry.get(
                "part_of_speech"
            )

            for definition in entry.get(
                "definitions", []
            ):

                cursor.execute(
                    """
                    INSERT INTO definitions (
                        word_id,
                        part_of_speech,
                        definition,
                        position
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        word_id,
                        part_of_speech,
                        definition,
                        position
                    )
                )

                position += 1

        # Variants
        for variant in record.get(
            "variants", []
        ):

            cursor.execute(
                """
                INSERT INTO variants (
                    word_id,
                    variant
                )
                VALUES (?, ?)
                """,
                (
                    word_id,
                    variant
                )
            )

    conn.commit()

    # ----------------------------------------
    # Validation
    # ----------------------------------------

    word_count = cursor.execute(
        "SELECT COUNT(*) FROM words"
    ).fetchone()[0]

    definition_count = cursor.execute(
        "SELECT COUNT(*) FROM definitions"
    ).fetchone()[0]

    variant_count = cursor.execute(
        "SELECT COUNT(*) FROM variants"
    ).fetchone()[0]

    pronunciation_count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM words
        WHERE ipa IS NOT NULL
        """
    ).fetchone()[0]

    conn.close()

    print()
    print("=" * 60)
    print("DATABASE BUILD COMPLETE")
    print("=" * 60)
    print(f"Words:            {word_count}")
    print(f"Definitions:      {definition_count}")
    print(f"Variants:         {variant_count}")
    print(f"With IPA:         {pronunciation_count}")
    print()
    print(f"Database: {DB_FILE}")


if __name__ == "__main__":
    main()
