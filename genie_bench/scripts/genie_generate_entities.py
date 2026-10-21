

import json
import time
from pathlib import Path

import requests

from genie_bench.ripple_get_most_viewed import HEADERS

ROOT = Path(__file__).resolve().parents[2]   # genie_bench/scripts/x.py -> repo root
OUT_PATH = ROOT / "artifacts" / "bench_generation" / "work_entities.json"
SPARQL = "https://query.wikidata.org/sparql"

# threshold per class: 60 sitelinks is ordinary for a film, exceptional for a building
WORK_CLASSES = {
    "Q11424":     ("film", 60),
    "Q7725634":   ("literary work", 60),
    "Q4830453":   ("business", 60),
    "Q3305213":   ("painting", 20),
    "Q105543609": ("musical work", 20),
    "Q7889":      ("video game", 30),
    "Q41176":     ("building", 20),
}


def fetch_works(class_qid, min_sitelinks, limit=300, attempts=3):

    query = f"""
        SELECT ?item ?itemLabel WHERE {{
          {{ SELECT ?item WHERE {{
               ?item wdt:P31 wd:{class_qid} ; wikibase:sitelinks ?n .
               FILTER(?n > {min_sitelinks})
             }} LIMIT {limit} }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}"""
    for attempt in range(attempts):
        r = requests.get(SPARQL, params={"query": query}, timeout=120,
                         headers={**HEADERS, "Accept": "application/sparql-results+json"})
        if r.status_code == 200:
            return {b["item"]["value"].rsplit("/", 1)[-1]: b["itemLabel"]["value"]
                    for b in r.json()["results"]["bindings"]
                    if not b["itemLabel"]["value"].startswith("Q")}   # no english label
        print(f"    http {r.status_code}, retry {attempt + 1}/{attempts} in 20s")
        time.sleep(20)
    return {}


def main():
    results = json.loads(OUT_PATH.read_text()) if OUT_PATH.exists() else {}

    for class_qid, (name, threshold) in WORK_CLASSES.items():
        if results.get(name):
            print(f"{name}: {len(results[name])} cached")
            continue
        works = fetch_works(class_qid, threshold)
        results[name] = works
        print(f"{name}: {len(works)} works")
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    print(f"{sum(len(v) for v in results.values())} entities -> {OUT_PATH}")


if __name__ == "__main__":
    main()