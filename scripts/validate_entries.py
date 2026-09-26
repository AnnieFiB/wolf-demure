import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "wiktionary"
    / "pidgin_enriched.json"
)


VALID_PARTS_OF_SPEECH = {
    "noun",
    "verb",
    "adjective",
    "adverb",
    "pronoun",
    "interjection",
    "preposition",
    "conjunction",
    "determiner",
    "numeral",
    "particle",
    "article",
    "proper noun",
}


def main():

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    missing_definitions = []
    invalid_pos = []
    duplicate_definitions = []

    for record in records:

        word = record["pidgin"]
        entries = record.get("entries", [])

        # No definitions
        if not entries:
            missing_definitions.append(word)

        seen = set()

        for entry in entries:

            pos = entry.get("part_of_speech")

            # Invalid part of speech
            if pos not in VALID_PARTS_OF_SPEECH:
                invalid_pos.append(
                    (word, pos)
                )

            # Duplicate definitions
            for definition in entry.get("definitions", []):

                key = definition.lower().strip()

                if key in seen:
                    duplicate_definitions.append(
                        (word, definition)
                    )

                seen.add(key)

    print()
    print("=" * 50)
    print("WOLF DEMURE DATA VALIDATION")
    print("=" * 50)

    print(f"Total words:              {len(records)}")
    print(f"Missing definitions:      {len(missing_definitions)}")
    print(f"Invalid parts of speech:  {len(invalid_pos)}")
    print(f"Duplicate definitions:    {len(duplicate_definitions)}")

    print()

    if missing_definitions:
        print("WORDS WITHOUT DEFINITIONS")
        print("-" * 50)

        for word in missing_definitions:
            print(word)

    if invalid_pos:
        print()
        print("INVALID PARTS OF SPEECH")
        print("-" * 50)

        for word, pos in invalid_pos:
            print(f"{word}: {pos}")

    if duplicate_definitions:
        print()
        print("DUPLICATE DEFINITIONS")
        print("-" * 50)

        for word, definition in duplicate_definitions:
            print(f"{word}: {definition}")


if __name__ == "__main__":
    main()
