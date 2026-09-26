import requests
import re
import json
import time
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

API_URL = "https://en.wiktionary.org/w/api.php"

HEADERS = {
    "User-Agent": "WolfDemure/0.1 (Nigerian Pidgin dictionary project)"
}

REQUEST_DELAY = 1.5
MAX_RETRIES = 5


# ============================================================
# Get complete Wiktionary page
# ============================================================

def get_wikitext(word, max_retries=MAX_RETRIES):

    params = {
        "action": "parse",
        "page": word,
        "prop": "wikitext",
        "format": "json",
        "formatversion": 2
    }

    for attempt in range(max_retries):

        try:

            response = requests.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=30
            )

            # ----------------------------------------
            # Success
            # ----------------------------------------

            if response.status_code == 200:

                data = response.json()

                return data["parse"]["wikitext"]

            # ----------------------------------------
            # Rate limited
            # ----------------------------------------

            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                if retry_after:

                    try:
                        wait_time = int(retry_after)

                    except ValueError:
                        wait_time = 5 * (2 ** attempt)

                else:

                    # Exponential backoff:
                    # 5, 10, 20, 40, 80 seconds
                    wait_time = 5 * (2 ** attempt)

                print(
                    f"    Rate limited (429). "
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)

                continue

            # ----------------------------------------
            # Other HTTP errors
            # ----------------------------------------

            response.raise_for_status()

        except requests.exceptions.RequestException as error:

            if attempt == max_retries - 1:
                raise

            wait_time = 5 * (2 ** attempt)

            print(
                f"    Network error: {error}"
            )

            print(
                f"    Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise Exception(
        f"Failed to retrieve '{word}' "
        f"after {max_retries} attempts."
    )


# ============================================================
# Extract only the Nigerian Pidgin section
# ============================================================

def extract_pidgin_section(wikitext):

    match = re.search(
        r"==Nigerian Pidgin==(.*?)(?=\n==[^=]|\Z)",
        wikitext,
        re.DOTALL
    )

    if match:
        return match.group(1).strip()

    return None


# ============================================================
# Clean basic Wiktionary markup
# ============================================================

def clean_wikitext(text):

    # [[word|display text]] -> display text
    text = re.sub(
        r"\[\[([^|\]]+)\|([^\]]+)\]\]",
        r"\2",
        text
    )

    # [[trouble]] -> trouble
    text = re.sub(
        r"\[\[([^\]]+)\]\]",
        r"\1",
        text
    )

    # Remove simple Wiktionary templates
    text = re.sub(
        r"\{\{[^{}]*\}\}",
        "",
        text
    )

    # Remove bold markup
    text = text.replace("'''", "")

    # Remove italic markup
    text = text.replace("''", "")

    # Collapse multiple spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip(" ,.;")


# ============================================================
# Extract alternative forms / spelling variants
# ============================================================

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

    # ----------------------------------------
    # Capture [[word]]
    # or [[word|display]]
    # ----------------------------------------

    links = re.findall(
        r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]",
        alternative_section
    )

    variants.extend(links)

    # ----------------------------------------
    # Capture:
    # {{alter|pcm|word}}
    # {{alter|pcm|word1|word2}}
    # ----------------------------------------

    alter_templates = re.findall(
        r"\{\{alter\|pcm\|([^}]+)\}\}",
        alternative_section
    )

    for template in alter_templates:

        parts = template.split("|")

        for part in parts:

            part = part.strip()

            # Ignore template parameters
            if part and "=" not in part:
                variants.append(part)

    # Remove duplicates while preserving order
    variants = list(
        dict.fromkeys(variants)
    )

    return variants


# ============================================================
# Extract pronunciation
# ============================================================

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

    # ----------------------------------------
    # IPA
    #
    # Example:
    # {{IPA|pcm|/something/}}
    # ----------------------------------------

    ipa_match = re.search(
        r"\{\{IPA\|pcm\|([^}|]+)",
        pronunciation_section
    )

    if ipa_match:

        pronunciation["ipa"] = (
            ipa_match.group(1).strip()
        )

    # ----------------------------------------
    # Audio
    #
    # Example:
    # {{audio|pcm|filename.ogg}}
    # ----------------------------------------

    audio_match = re.search(
        r"\{\{audio\|pcm\|([^}|]+)",
        pronunciation_section,
        re.IGNORECASE
    )

    if audio_match:

        pronunciation["audio"] = (
            audio_match.group(1).strip()
        )

    return pronunciation


# ============================================================
# Extract parts of speech and definitions
# ============================================================
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


# ============================================================
# Parse one Wiktionary word
# ============================================================

def parse_word(word):

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


# ============================================================
# Save checkpoint
# ============================================================

def save_results(results, output_file):

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# Main ETL process
# ============================================================

def main():

    # --------------------------------------------------------
    # Paths
    # --------------------------------------------------------

    base_dir = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    input_file = (
        base_dir
        / "data"
        / "raw"
        / "wiktionary"
        / "pidgin_lemmas.json"
    )

    output_file = (
        base_dir
        / "data"
        / "raw"
        / "wiktionary"
        / "pidgin_enriched.json"
    )

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not input_file.exists():

        raise FileNotFoundError(
            f"Input file not found: {input_file}"
        )

    # --------------------------------------------------------
    # Load lemmas
    # --------------------------------------------------------

    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as file:

        lemmas = json.load(file)

    total = len(lemmas)

    print()
    print("=" * 60)
    print("WOLF DEMURE — WIKTIONARY ENRICHMENT")
    print("=" * 60)

    print(
        f"Found {total} Nigerian Pidgin lemmas."
    )

    print()

    # --------------------------------------------------------
    # Resume previous run
    # --------------------------------------------------------

    if output_file.exists():

        try:

            with open(
                output_file,
                "r",
                encoding="utf-8"
            ) as file:

                results = json.load(file)

            print(
                f"Existing checkpoint found: "
                f"{len(results)} records."
            )

        except json.JSONDecodeError:

            print(
                "Existing output file is invalid. "
                "Starting from scratch."
            )

            results = []

    else:

        results = []

    # --------------------------------------------------------
    # Only treat successful/non-error records as processed
    #
    # This is important:
    # previous 429/error records should be retried.
    # --------------------------------------------------------

    processed_words = {
        item["pidgin"]
        for item in results
        if item.get("status") != "error"
    }

    # Remove previous error records.
    # They'll be attempted again during this run.

    results = [
        item
        for item in results
        if item.get("status") != "error"
    ]

    if processed_words:

        print(
            f"Resuming with "
            f"{len(processed_words)} successful "
            f"records already completed."
        )

        print()

    # --------------------------------------------------------
    # Process every lemma
    # --------------------------------------------------------

    for number, lemma in enumerate(
        lemmas,
        start=1
    ):

        word = lemma["word"]
        pageid = lemma["pageid"]

        # ----------------------------------------
        # Already completed
        # ----------------------------------------

        if word in processed_words:

            print(
                f"[{number}/{total}] "
                f"Skipping: {word}"
            )

            continue

        print(
            f"[{number}/{total}] "
            f"Processing: {word}"
        )

        try:

            result = parse_word(word)

            # Preserve Wiktionary page ID
            result["pageid"] = pageid

            results.append(result)

            processed_words.add(word)

            print("    ✓ Success")

        except Exception as error:

            print(
                f"    ✗ ERROR: {error}"
            )

            results.append({
                "pidgin": word,
                "pageid": pageid,
                "status": "error",
                "error": str(error)
            })

        # ----------------------------------------
        # CHECKPOINT
        #
        # Save after every word so progress
        # isn't lost if the script stops.
        # ----------------------------------------

        save_results(
            results,
            output_file
        )

        # ----------------------------------------
        # Be polite to Wiktionary
        # ----------------------------------------

        time.sleep(
            REQUEST_DELAY
        )

    # --------------------------------------------------------
    # Final save
    # --------------------------------------------------------

    save_results(
        results,
        output_file
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    successful = [
        item
        for item in results
        if item.get("status") != "error"
    ]

    errors = [
        item
        for item in results
        if item.get("status") == "error"
    ]

    no_section = [
        item
        for item in results
        if item.get("status")
        == "no_nigerian_pidgin_section"
    ]

    with_entries = [
        item
        for item in results
        if item.get("entries")
    ]

    with_pronunciation = [
        item
        for item in results
        if (
            item.get("pronunciation", {}).get("ipa")
            or
            item.get("pronunciation", {}).get("audio")
        )
    ]

    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)

    print(
        f"Total lemmas:           {total}"
    )

    print(
        f"Successful records:     {len(successful)}"
    )

    print(
        f"Records with entries:   {len(with_entries)}"
    )

    print(
        f"No Pidgin section:      {len(no_section)}"
    )

    print(
        f"With pronunciation:     {len(with_pronunciation)}"
    )

    print(
        f"Errors:                 {len(errors)}"
    )

    print()

    print(
        f"Saved to:\n{output_file}"
    )

    # --------------------------------------------------------
    # Display errors
    # --------------------------------------------------------

    if errors:

        print()
        print("Failed entries:")
        print("-" * 60)

        for item in errors:

            print(
                f"{item['pidgin']}: "
                f"{item['error']}"
            )


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()
