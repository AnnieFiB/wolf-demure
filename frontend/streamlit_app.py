
import sys
from pathlib import Path
import streamlit as st


# ============================================================
# Project setup
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from services.dictionary import search_dictionary


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="Wolf Demure",
    page_icon="🐺",
    layout="centered"
)


# ============================================================
# Compact styling
# ============================================================

st.markdown(
    """
    <style>

    /* Reduce space between result blocks */
    .result-block {
        margin-top: 0.8rem;
        margin-bottom: 1rem;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid rgba(128,128,128,0.25);
    }

    /* Result word */
    .result-word {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        padding: 0;
    }

    /* Pronunciation */
    .pronunciation {
        margin-top: 0.2rem;
        margin-bottom: 0.4rem;
        font-size: 1rem;
    }

    /* Part of speech */
    .part-of-speech {
        font-size: 0.8rem;
        opacity: 0.65;
        text-transform: uppercase;
        margin-top: 0.5rem;
        margin-bottom: 0.1rem;
    }

    /* Definition */
    .definition {
        font-size: 1rem;
        margin-top: 0;
        margin-bottom: 0.25rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# Header
# ============================================================

st.title("🐺 Wolf Demure")
st.subheader("Nigerian Pidgin Dictionary v2")


# ============================================================
# Search form
# Enter OR Search button
# ============================================================

with st.form("search_form"):

    query = st.text_input(
        "Enter a Pidgin or English word",
        placeholder="e.g. wahala, trouble, eat, patapata"
    )

    search = st.form_submit_button("Search")


# ============================================================
# Search results
# ============================================================

if search:

    query = query.strip()

    if not query:

        st.warning("Enter a word to search.")

    else:

        results = search_dictionary(query)

        if not results:

            st.warning(
                f"No definition found for '{query}'."
            )

        else:

            # Group rows by word
            grouped = {}

            for row in results:

                word = row["word"]

                if word not in grouped:

                    grouped[word] = {
                        "ipa": row["ipa"],
                        "entries": []
                    }

                grouped[word]["entries"].append({
                    "part_of_speech": row["part_of_speech"],
                    "definition": row["definition"]
                })


            # ================================================
            # Display results
            # ================================================

            for word, data in grouped.items():

                html = '<div class="result-block">'

                # Word
                html += (
                    f'<div class="result-word">'
                    f'{word}'
                    f'</div>'
                )

                # Pronunciation
                if data["ipa"]:

                    html += (
                        f'<div class="pronunciation">'
                        f'🔊 <b>Pronunciation:</b> '
                        f'{data["ipa"]}'
                        f'</div>'
                    )

                # Definitions
                for entry in data["entries"]:

                    part_of_speech = entry[
                        "part_of_speech"
                    ]

                    definition = entry[
                        "definition"
                    ]

                    if part_of_speech:

                        html += (
                            f'<div class="part-of-speech">'
                            f'{part_of_speech}'
                            f'</div>'
                        )

                    if definition:

                        html += (
                            f'<div class="definition">'
                            f'{definition}'
                            f'</div>'
                        )

                html += '</div>'

                st.markdown(
                    html,
                    unsafe_allow_html=True
                )
