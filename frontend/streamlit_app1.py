
import streamlit as st
import json
from pathlib import Path


# -------------------------
# Page configuration
# -------------------------

st.set_page_config(
    page_title="Wolf Demure",
    page_icon="🐺",
    layout="centered"
)


# -------------------------
# Load dictionary
# -------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DICTIONARY_FILE = BASE_DIR / "data" / "pidgin_dictionary.json"


@st.cache_data
def load_dictionary():
    with open(DICTIONARY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


dictionary = load_dictionary()


# -------------------------
# App
# -------------------------

st.title("🐺 Wolf Demure")

st.write("Nigerian Pidgin Dictionary .v1")

word = st.text_input(
    "Enter a Pidgin or English word",
    placeholder="e.g. wahala, trouble, abeg, please"
)


# -------------------------
# Search
# -------------------------

if st.button("Search"):

    if not word:

        st.warning("Enter a word or phrase first.")

    else:

        query = word.lower().strip()

        results = []

        for entry in dictionary:

            pidgin = entry["pidgin"].lower()
            english = entry["english"].lower()

            if query in pidgin or query in english:
                results.append(entry)


        # -------------------------
        # Display results
        # -------------------------

        if results:

            st.write(f"Found {len(results)} result(s)")

            for result in results:

                st.subheader(result["pidgin"])

                st.write(
                    f"**English:** {result['english']}"
                )

                st.write(
                    f"**Example:** {result['example']}"
                )

                st.divider()

        else:

            st.warning(
                f"No definition found for '{word}'."
            )
