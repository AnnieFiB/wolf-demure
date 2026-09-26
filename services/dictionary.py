
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "data" / "processed" / "wolf_demure.db"

RESULT_COLUMNS = """
SELECT w.id,w.word,w.word_normalized,w.entry_type,w.ipa,w.phonetic,w.audio,
       d.part_of_speech,d.definition,d.position,d.source
"""

IRREGULAR = {
    "eat":["eat","eats","eating","eaten","ate"],
    "go":["go","goes","going","gone","went"],
    "come":["come","comes","coming","came"],
    "give":["give","gives","giving","gave","given"],
    "take":["take","takes","taking","took","taken"],
    "see":["see","sees","seeing","saw","seen"],
    "say":["say","says","saying","said"],
    "get":["get","gets","getting","got","gotten"],
    "make":["make","makes","making","made"],
    "do":["do","does","doing","did","done"],
    "be":["be","being","been","am","is","are","was","were"],
    "have":["have","has","having","had"],
    "run":["run","runs","running","ran"],
    "drink":["drink","drinks","drinking","drank","drunk"],
    "speak":["speak","speaks","speaking","spoke","spoken"],
    "write":["write","writes","writing","wrote","written"],
    "buy":["buy","buys","buying","bought"],
    "bring":["bring","brings","bringing","brought"]
}

def get_connection():
    conn=sqlite3.connect(DB_FILE)
    conn.row_factory=sqlite3.Row
    return conn

def normalize(text):
    return " ".join(text.lower().strip().split()) if text else ""

def build_english_pattern(query):
    query=normalize(query)

    if " " in query:
        return re.compile(rf"(?<!\w){re.escape(query)}(?!\w)",re.I)

    if query in IRREGULAR:
        forms=IRREGULAR[query]
    else:
        forms=[query]
        if len(query)>=3:
            forms.append(query+"s")
            if query.endswith("e"):
                forms += [query[:-1]+"ing",query+"d"]
            else:
                forms += [query+"ing",query+"ed"]

    forms=sorted(set(forms),key=len,reverse=True)
    expr="|".join(re.escape(x) for x in forms)
    return re.compile(rf"(?<!\w)(?:{expr})(?!\w)",re.I)

def english_match_score(query,definition):
    query=normalize(query)
    definition=normalize(definition)

    if definition==query:
        return 0
    if re.match(rf"^{re.escape(query)}\b",definition):
        return 1
    if re.search(rf"(?<!\w){re.escape(query)}(?!\w)",definition,re.I):
        return 2
    return 3

def search_english(conn,query,limit):
    pattern=build_english_pattern(query)

    rows=conn.execute(f"""
        {RESULT_COLUMNS}
        FROM definitions d
        JOIN words w ON d.word_id=w.id
        ORDER BY w.word,d.position
    """).fetchall()

    matches=[]

    for row in rows:
        definition=row["definition"] or ""
        if not pattern.search(definition):
            continue

        matches.append((
            english_match_score(query,definition),
            len(definition),
            row["word"].lower(),
            row["position"] or 0,
            dict(row)
        ))

    matches.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
    return [x[4] for x in matches[:limit]]

def search_dictionary(query,limit=50):
    query=normalize(query)
    if not query:
        return []

    conn=get_connection()

    try:
        rows=conn.execute(f"""
            {RESULT_COLUMNS}
            FROM words w
            LEFT JOIN definitions d ON w.id=d.word_id
            WHERE w.word_normalized=?
            ORDER BY d.position
        """,(query,)).fetchall()

        if rows:
            return [dict(r) for r in rows]

        rows=conn.execute(f"""
            {RESULT_COLUMNS}
            FROM variants v
            JOIN words w ON v.word_id=w.id
            LEFT JOIN definitions d ON w.id=d.word_id
            WHERE LOWER(v.variant)=?
            ORDER BY d.position
        """,(query,)).fetchall()

        if rows:
            return [dict(r) for r in rows]

        rows=conn.execute(f"""
            {RESULT_COLUMNS}
            FROM words w
            LEFT JOIN definitions d ON w.id=d.word_id
            WHERE w.word_normalized LIKE ?
            ORDER BY LENGTH(w.word_normalized),w.word,d.position
            LIMIT ?
        """,(f"{query}%",limit)).fetchall()

        if rows:
            return [dict(r) for r in rows]

        return search_english(conn,query,limit)

    finally:
        conn.close()

def get_word_variants(word_id):
    conn=get_connection()
    try:
        rows=conn.execute("""
            SELECT variant
            FROM variants
            WHERE word_id=?
            ORDER BY variant
        """,(word_id,)).fetchall()
        return [r["variant"] for r in rows]
    finally:
        conn.close()

def get_suggestions(query,limit=8):
    query=normalize(query)
    if not query:
        return []

    conn=get_connection()

    try:
        rows=conn.execute("""
            SELECT word,entry_type
            FROM words
            WHERE word_normalized LIKE ?
            ORDER BY
                CASE WHEN word_normalized=? THEN 0 ELSE 1 END,
                LENGTH(word_normalized),
                word
            LIMIT ?
        """,(f"{query}%",query,limit)).fetchall()

        suggestions=[
            {"word":r["word"],"entry_type":r["entry_type"]}
            for r in rows
        ]

        # Also suggest canonical words when query begins a variant
        remaining=limit-len(suggestions)

        if remaining>0:
            rows=conn.execute("""
                SELECT DISTINCT w.word,w.entry_type
                FROM variants v
                JOIN words w ON v.word_id=w.id
                WHERE LOWER(v.variant) LIKE ?
                ORDER BY LENGTH(v.variant),w.word
                LIMIT ?
            """,(f"{query}%",remaining)).fetchall()

            existing={x["word"].lower() for x in suggestions}

            for r in rows:
                if r["word"].lower() not in existing:
                    suggestions.append({
                        "word":r["word"],
                        "entry_type":r["entry_type"]
                    })

        return suggestions[:limit]

    finally:
        conn.close()
