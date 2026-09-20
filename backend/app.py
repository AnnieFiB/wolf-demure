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
    return {
        "message": "Wolf Demure API is running"
    }


@app.get("/search")
def search(word: str):

    word = word.lower().strip()

    for entry in dictionary:

        if entry["pidgin"].lower() == word:

            return {
                "found": True,
                "result": entry
            }

    return {
        "found": False,
        "message": f"No definition found for '{word}'"
    }
