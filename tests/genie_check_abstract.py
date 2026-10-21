"""Fixture check for the abstract_2 / abstract_3 templates.

    uv run python tests/genie_check_abstract.py

Handcrafted rows, one per branch, asserting the exact prompt string and the recorded
constraints. No table, no model, no network — runs in under a second.

The point is to catch a wrong template, a stray None in a format string, or the
"different relation" exclusion failing, BEFORE any of it is baked into 7,340 records.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genie_bench.scripts.genie_full_generation import (
    abstract_2, abstract_3, build_person_index)


def row(subject, cls, frame, year, sitelinks, relation, pid, obj, alt):
    "the shape genie_table.json rows have, trimmed to what the makers read"
    return {
        "subject": {"label": subject, "class": cls, "discursive_frame": frame,
                    "year": year, "sitelinks": sitelinks},
        "relation": {"name": relation, "pid": pid},
        "object": {"label": obj, "class_qid": "Q5", "gender_qid": "Q6581097",
                   "sitelinks": 58},
        "alt": {"label": alt},
    }


# The table the index is built from. Breakfast at Tiffany's has TWO relations, so the
# maker must narrow by the one that is not being edited.
TABLE = [
    row("Breakfast at Tiffany's", "film", "work", 1961, 62,
        "director", "P57", "Blake Edwards", "Wes Craven"),
    row("Breakfast at Tiffany's", "film", "work", 1961, 62,
        "composer", "P86", "Henry Mancini", "Brian Wilson"),
    row("Obscure Short", "film", "work", 1961, 4,
        "director", "P57", "Nobody Much", "Someone Else"),
    row("Lenovo", "company", "org", 1984, 55,
        "founder", "P112", "Liu Chuanzhi", "Elon Musk"),
    row("Lenovo", "company", "org", 1984, 55,
        "headquarters", "P159", "Ren Zhengfei", "Tim Cook"),
]
# a subject with no person on any other relation -> year-only fallback
LONELY = row("Solo Work", "film", "work", 1999, 80,
             "director", "P57", "Only Director", "Other Director")


def check(label, got, want):
    ok = got == want
    print(f"  {'ok ' if ok else 'BAD'}  {label}")
    if not ok:
        print(f"        got  {got!r}\n        want {want!r}")
    return ok


def main() -> int:
    build_person_index(TABLE)
    ok = True

    # 1. edit the DIRECTOR -> must narrow by the composer, never the director
    p = abstract_3(TABLE[0])
    ok &= check("abstract_3 work, edit=director, narrows by composer", p["prompt"],
                "Henry Mancini films from 1961 are often remembered for their "
                "production. One example")
    ok &= check("  constraints", p["constraints"], ["year", "person"])

    # 2. edit the COMPOSER -> must narrow by the director. The exclusion is the test.
    p = abstract_3(TABLE[1])
    ok &= check("abstract_3 work, edit=composer, narrows by director", p["prompt"],
                "Blake Edwards films from 1961 are often remembered for their "
                "music. One example")

    # 3. below the prominence gate -> no probe at all
    ok &= check("abstract_3 gated out below ABSTRACT_3_MIN_SITELINKS",
                abstract_3(TABLE[2]), None)

    # 4. org frame, person variant — and consonant+y pluralises correctly
    p = abstract_3(TABLE[3])
    ok &= check("abstract_3 org", p["prompt"],
                "Ren Zhengfei companies founded in 1984 are often remembered for "
                "their origins. One example")

    # 5. no person available anywhere -> year-only fallback, no None in the string
    build_person_index([LONELY])
    p = abstract_3(LONELY)
    ok &= check("abstract_3 fallback, no person", p["prompt"],
                "films from 1999 are often remembered for their production. One example")
    ok &= check("  constraints", p["constraints"], ["year"])

    # 6. abstract_2 gains the person, phrasing A
    build_person_index(TABLE)
    p = abstract_2(TABLE[0])
    ok &= check("abstract_2 work with person", p["prompt"],
                "Breakfast at Tiffany's is a 1961 Henry Mancini film. Its production")
    ok &= check("  constraints", p["constraints"], ["subject", "person"])

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
