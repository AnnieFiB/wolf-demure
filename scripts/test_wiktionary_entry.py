import requests
import re
import json


API_URL = "https://en.wiktionary.org/w/api.php"

HEADERS = {
    "User-Agent": "WolfDemure/0.1 (Nigerian Pidgin dictionary project)"
}

TEST_WORDS = [
    "swit",
    "hyar",
    "Naija",
    "tu",
    "waka"
]


# --------------------------------------------------
# Get complete Wiktionary page
# --------------------------------------------------

def get_wikitext(word):

    params = {
        "action": "parse",
        "page": word,
        "prop": "wikitext",
        "format": "json",
        "formatversion": 2
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data["parse"]["wikitext"]


# --------------------------------------------------
# Extract only Nigerian Pidgin section
# --------------------------------------------------

def extract_pidgin_section(wikitext):

    match = re.search(
        r"==Nigerian Pidgin==(.*?)(?=\n==[^=]|\Z)",
        wikitext,
        re.DOTALL
    )

    if match:
        return match.group(1).strip()

    return None


# --------------------------------------------------
# Clean basic Wiktionary markup
# --------------------------------------------------

def clean_wikitext(text):

    # [[trouble]] -> trouble
    text = re.sub(
        r"\[\[([^|\]]+)\]\]",
        r"\1",
        text
    )

    # [[word|display text]] -> display text
    text = re.sub(
        r"\[\[([^|\]]+)\|([^\]]+)\]\]",
        r"\2",
        text
    )

    # Remove simple templates
    text = re.sub(
        r"\{\{[^{}]*\}\}",
        "",
        text
    )

    # Remove bold/italic markup
    text = text.replace("'''", "")
    text = text.replace("''", "")

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip(" ,.;")


# --------------------------------------------------
# Extract alternative forms
# --------------------------------------------------

def extract_variants(section):

    variants = []

    match = re.search(
        r"===Alternative forms===(.*?)(?=\n===|\Z)",
        section,
        re.DOTALL
    )

    if not match:
        return variants

    alternative_section = match.group(1)

    # Capture links such as [[word]]
    links = re.findall(
        r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]",
        alternative_section
    )

    variants.extend(links)

    # Capture {{alter|pcm|word|word2}}
    alter_templates = re.findall(
        r"\{\{alter\|pcm\|([^}]+)\}\}",
        alternative_section
    )

    for template in alter_templates:

        parts = template.split("|")

        for part in parts:

            part = part.strip()

            if part and "=" not in part:
                variants.append(part)

    return list(dict.fromkeys(variants))


# --------------------------------------------------
# Extract pronunciation
# --------------------------------------------------

def extract_pronunciation(section):

    pronunciation = {
        "ipa": None,
        "phonetic": None,
        "audio": None
    }

    match = re.search(
        r"===Pronunciation===(.*?)(?=\n===|\Z)",
        section,
        re.DOTALL
    )

    if not match:
        return pronunciation

    pronunciation_section = match.group(1)

    # Look for explicit IPA templates
    ipa_match = re.search(
        r"\{\{IPA\|pcm\|([^}|]+)",
        pronunciation_section
    )

    if ipa_match:
        pronunciation["ipa"] = ipa_match.group(1).strip()

    # Look for audio template
    audio_match = re.search(
        r"\{\{audio\|pcm\|([^}|]+)",
        pronunciation_section,
        re.IGNORECASE
    )

    if audio_match:
        pronunciation["audio"] = audio_match.group(1).strip()

    return pronunciation


# --------------------------------------------------
# Extract parts of speech and definitions
# --------------------------------------------------

def extract_entries(section):

    entries = []

    valid_pos = {
        "noun",
        "proper noun",
        "verb",
        "adjective",
        "adverb",
        "pronoun",
        "interjection",
        "preposition",
        "conjunction",
        "determiner",
        "article",
        "numeral",
        "particle"
    }

    # Match both:
    # ===Noun===
    # ====Noun====
    headings = list(
        re.finditer(
            r"^(={3,4})([^=]+)\1$",
            section,
            re.MULTILINE
        )
    )

    for index, heading in enumerate(headings):

        title = heading.group(2).strip()
        pos = title.lower()

        # Ignore anything that isn't a part of speech
        if pos not in valid_pos:
            continue

        start = heading.end()

        if index + 1 < len(headings):
            end = headings[index + 1].start()
        else:
            end = len(section)

        content = section[start:end]

        definitions = []

        for line in content.splitlines():

            if re.match(r"^#(?![#*:])", line):

                definition = re.sub(
                    r"^#\s*",
                    "",
                    line
                )

                definition = clean_wikitext(
                    definition
                )

                if definition:
                    definitions.append(definition)

        if definitions:

            entries.append({
                "part_of_speech": pos,
                "definitions": definitions
            })

    return entries

# --------------------------------------------------
# Parse one word
# --------------------------------------------------

def parse_word(word):

    print(f"Processing: {word}")

    wikitext = get_wikitext(word)

    section = extract_pidgin_section(
        wikitext
    )

    if not section:

        return {
            "pidgin": word,
            "status": "no_nigerian_pidgin_section"
        }

    return {
        "pidgin": word,
        "entries": extract_entries(section),
        "pronunciation": extract_pronunciation(section),
        "variants": extract_variants(section),
        "source": "Wiktionary"
    }


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    results = []

    for word in TEST_WORDS:

        try:

            result = parse_word(word)

            results.append(result)

        except Exception as error:

            results.append({
                "pidgin": word,
                "status": "error",
                "error": str(error)
            })

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
