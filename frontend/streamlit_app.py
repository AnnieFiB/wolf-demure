
import streamlit as st
import requests

# Address of our FastAPI backend
API_URL = "http://127.0.0.1:8000"

# Page configuration
st.set_page_config(
    page_title="Wolf Demure",
    page_icon="🐺",
    layout="centered"
)

# App heading
st.title("🐺 Wolf Demure")
st.write("Nigerian Pidgin Dictionary")

# Search box
word = st.text_input(
    "Enter a Pidgin word or phrase",
    placeholder="e.g. how far"
)

# Search button
if st.button("Search"):

    if not word:
        st.warning("Enter a word or phrase first.")

    else:
        try:
            response = requests.get(
                f"{API_URL}/search",
                params={"word": word}
            )

            data = response.json()

            if data["found"]:

                result = data["result"]

                st.success(result["english"])

                st.subheader("Example")
                st.write(result["example"])

            else:
                st.warning(
                    f"No definition found for '{word}'."
                )

        except requests.exceptions.ConnectionError:

            st.error(
                "Cannot connect to the Wolf Demure API."
            )
