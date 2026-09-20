## Build the backend

from fastapi import FastAPI
import json
from pathlib import Path

app = FastAPI(title="Wolf Demure Pidgin Dictionary")

# Find dictionary file
BASE_DIR = Path(__file__).resolve().parent.parent
DICTIONARY_FILE = BASE_DIR / "data" / "pidgin_dictionary.json"

# Load dictionary
with open(DICTIONARY_FILE, "r", encoding="utf-8") as file:
    dictionary = json.load(file)


@app.get("/")
def home():
    return { "message": "Wolf Demure API is running" }

@app.get("/search")
def search(word: str):
    # Clean what the user typed
    query = word.lower().strip()

    results = []

    # Search every dictionary entry
    for entry in dictionary:
        pidgin = entry["pidgin"].lower()
        english = entry["english"].lower()

        # Search both Pidgin and English
        if query in pidgin or query in english:
            results.append(entry)

    # Return matches
    if results:
        return {
            "found": True,
            "count": len(results),
            "results": results
        }

    # Nothing found
    return {
        "found": False,
        "count": 0,
        "results": [],
        "message": f"No definition found for '{word}'"
    }
