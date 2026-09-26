
import json
from pathlib import Path

import requests


API_URL = "https://en.wiktionary.org/w/api.php"
HEADERS = {
    "User-Agent": "WolfDemure/0.1 (Nigerian Pidgin dictionary project)"
}
CATEGORY = "Category:Nigerian Pidgin lemmas"


# Work out where the project root is
BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "wiktionary"
    / "pidgin_lemmas.json"
)


def get_pidgin_words():

    words = []

    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": CATEGORY,
        "cmnamespace": 0,
        "cmlimit": 500,
        "format": "json"
    }

    print("Connecting to Wiktionary...")

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    print(f"Status code: {response.status_code}")

    response.raise_for_status()
    data = response.json()
    members = data["query"]["categorymembers"]

    for member in members:

        words.append({
            "pageid": member["pageid"],
            "word": member["title"]
        })

    return words


def save_words(words):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            words,
            file,
            ensure_ascii=False,
            indent=2
        )


def main():

    words = get_pidgin_words()

    save_words(words)

    print()
    print(f"Downloaded {len(words)} Nigerian Pidgin words.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
