
import sys
from html import escape
from pathlib import Path
import streamlit as st

BASE_DIR=Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path: sys.path.append(str(BASE_DIR))

from services.dictionary import search_dictionary,get_word_variants
from services.corpus import get_word_examples

st.set_page_config(page_title="Wolf Demure v2",page_icon="🐺",layout="centered")

st.markdown("""
<style>
.block-container{padding-top:2rem;max-width:760px}
.result-block{margin:.7rem 0 .2rem}
.result-word{font-size:1.7rem;font-weight:700;line-height:1.15;color:inherit}
.entry-type,.part-of-speech{font-size:.72rem;font-weight:600;color:#999;text-transform:uppercase;margin:.15rem 0}
.pronunciation{font-size:.95rem;color:#bbb;margin:.1rem 0 .25rem}
.variant{font-size:.85rem;color:#999;margin:.1rem 0 .3rem}
.definition-block{margin:.3rem 0 .5rem}
.definition{font-size:1rem;line-height:1.4;color:inherit}
.source{font-size:.72rem;color:#888}
.example-block{margin-bottom:.7rem}
.example-pidgin{font-weight:600;color:inherit}
.example-english{font-size:.9rem;color:#aaa}
.example-source{font-size:.7rem;color:#888}
div[data-testid="stButton"] button{border-color:#555!important;color:inherit!important}
div[data-testid="stButton"] button:hover{border-color:#888!important}
div[data-baseweb="select"]>div{border-color:#666!important}
div[data-baseweb="select"]>div:focus-within{border-color:#888!important;box-shadow:0 0 0 1px #888!important}
</style>
""",unsafe_allow_html=True)

# Load dictionary terms for autocomplete
@st.cache_data
def load_terms():
    import sqlite3
    db=BASE_DIR/"data"/"processed"/"wolf_demure.db"
    con=sqlite3.connect(db)
    rows=con.execute("""
        SELECT word FROM words
        UNION
        SELECT variant FROM variants
        ORDER BY word
    """).fetchall()
    con.close()
    return [r[0] for r in rows]

terms=load_terms()

st.title("🐺 Wolf Demure v2")
st.caption("Nigerian Pidgin Dictionary")

# Searchable autocomplete
query=st.selectbox(
    "Search Pidgin or English",
    options=terms,
    index=None,
    placeholder="Type Pidgin or English...",
    accept_new_options=True
)

search=st.button("Search",use_container_width=True)

if query and (search or query):
    results=search_dictionary(query)

    if not results:
        st.warning(f"No definition found for '{query}'.")

    else:
        grouped={}

        for r in results:
            wid=r["id"]

            if wid not in grouped:
                grouped[wid]={
                    "id":wid,
                    "word":r["word"],
                    "type":r.get("entry_type") or "word",
                    "ipa":r.get("ipa"),
                    "phonetic":r.get("phonetic"),
                    "definitions":[]
                }

            grouped[wid]["definitions"].append({
                "pos":r.get("part_of_speech"),
                "definition":r.get("definition"),
                "source":r.get("source")
            })

        if len(grouped)>1:
            st.caption(f"{len(grouped)} results")

        for i,data in enumerate(grouped.values()):

            variants=get_word_variants(data["id"])

            html=f"""
            <div class="result-block">
            <div class="result-word">{escape(data["word"])}</div>
            <div class="entry-type">{escape(data["type"])}</div>
            """

            pron=data["ipa"] or data["phonetic"]

            if pron:
                html+=f'<div class="pronunciation">/{escape(pron.strip("/"))}/</div>'

            if variants:
                html+=f'<div class="variant">Also: {escape(" · ".join(variants))}</div>'

            for d in data["definitions"]:

                if not d["definition"]: continue

                html+='<div class="definition-block">'

                if d["pos"]:
                    html+=f'<div class="part-of-speech">{escape(d["pos"])}</div>'

                html+=f'<div class="definition">{escape(d["definition"])}</div>'

                if d["source"]:
                    html+=f'<div class="source">{escape(d["source"])}</div>'

                html+='</div>'

            html+='</div>'
            st.markdown(html,unsafe_allow_html=True)

            examples=get_word_examples(data["word"],limit=3)

            if examples:
                with st.expander(f"Examples ({len(examples)})"):
                    for ex in examples:

                        html=f"""
                        <div class="example-block">
                        <div class="example-pidgin">
                        {escape(ex["pidgin_text"])}
                        </div>
                        """

                        if ex.get("english_text"):
                            html+=f'<div class="example-english">{escape(ex["english_text"])}</div>'

                        if ex.get("source"):
                            html+=f'<div class="example-source">{escape(ex["source"])}</div>'

                        html+='</div>'
                        st.markdown(html,unsafe_allow_html=True)

            if i<len(grouped)-1:
                st.divider()
