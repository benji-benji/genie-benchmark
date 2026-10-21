"""Popularity sampling of WikiData entities, taken from RippleEdits.

Adapted from the reference implementation at
https://github.com/edenbiran/RippleEdits (MIT; licence text reproduced in THIRD_PARTY_LICENSES.md). Paper:
Cohen, R., Biran, E., Yoran, O., Globerson, A. and Geva, M. (2024) 'Evaluating the
ripple effects of knowledge editing in language models', TACL. arXiv:2307.12976.

Follows the reference: the most-viewed-pages query against the Wikimedia pageviews
API and the title-to-QID resolution, so Genie filters for popularity on the same
basis RippleEdits does - which is what makes the selected subjects likely to be known
by the pre-trained model.

Author's own: the output paths, the monthly aggregation in `generate_monthly`, and
the request headers.
"""

import itertools
import json

import requests
from pathlib import Path

from genie_bench.ripple_relations import Ripple_Relation

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "artifacts" / "bench_generation" / "top_entities_by_views_monthly.json"

HEADERS = {"User-Agent": "most-viewed-entities/1.0 (benwbethell@gmail.com)"}

def query(request):
    request["action"] = "query"
    request["format"] = "json"
    last_continue = {}
    while True:
        # Clone original request
        req = request.copy()
        # Modify it with the values returned in the 'continue' section of the last result.
        req.update(last_continue)
        # Call API
        result = requests.get("https://en.wikipedia.org/w/api.php", params=req).json()
        if "error" in result:
            raise Exception(result["error"])
        if "warnings" in result:
            print(result["warnings"])
        if "query" in result:
            yield result["query"]
        if "continue" not in result:
            break
        last_continue = result["continue"]


# Follows the reference: title-to-QID resolution.
def get_wikidata_id_by_title(title):
    req = {"format": "json", "action": "query", "prop": "pageprops", "titles": title}
    result = requests.get("https://en.wikipedia.org/w/api.php", params=req).json()
    return list(result["query"]["pages"].values())[0]["pageprops"]["wikibase_item"]


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(itertools.islice(it, size)), ())


# Follows the reference: most-viewed-pages query against the Wikimedia pageviews API.
def get_top_pages_by_date(year, month, day):
    month = str(month).rjust(2, "0")
    if day == 0:
        day = "all-days"
    else:
        day = str(day).rjust(2, "0")
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia.org/all-access/{year}/{month}/{day}"
    headers = HEADERS
    pageview_results = requests.get(url, headers=headers).json()

    if "items" not in pageview_results:
        print(f"  no pageview data for {year}/{month}: "
              f"{pageview_results.get('title', 'unknown error')}")
        return []

    article_names = [
        page_info["article"] for page_info in pageview_results["items"][0]["articles"]
    ]
    wikidata_ids = dict()
    for batch in chunk(article_names, 50):
        pageprops_result = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "format": "json",
                "action": "query",
                "prop": "pageprops",
                "titles": "|".join(batch),
            },
            headers=HEADERS,
        ).json()
        pages = pageprops_result["query"]["pages"]
        for info in pages.values():
            try:
                wikidata_ids[info["title"]] = info["pageprops"]["wikibase_item"]
            except KeyError:
                # print(f'Failed getting info for {info}')
                pass

    wikidata_claims = dict()
    wanted_relations = set([relation.id() for relation in Ripple_Relation])
    for batch in chunk(wikidata_ids.values(), 50):
        claims_result = requests.get(
            "https://wikidata.org/w/api.php",
            params={
                "format": "json",
                "action": "wbgetentities",
                "prop": "claims",
                "languages": "en",
                "ids": "|".join(batch),
            },
            headers=HEADERS,
        ).json()
        for entity_id, entity_info in claims_result["entities"].items():
            claims = list(entity_info["claims"].keys())
            if any(x in wanted_relations for x in claims):
                wikidata_claims[entity_id] = claims

    top_pages = []
    articles = pageview_results["items"][0]["articles"]
    for page_info in articles:
        try:
            page = dict()
            page["title"] = page_info["article"].replace("_", " ")
            page["id"] = wikidata_ids[page["title"]]
            page["views"] = page_info["views"]
            if page["id"] in wikidata_claims:
                top_pages.append(page)
        except KeyError:
            # print(f'Failed getting info for {page_info}')
            pass

    return top_pages


def generate_monthly():
    results = dict()

    for year, month in [("2015", 9), ("2016", 6), ("2017", 6)]:
        month = str(month).rjust(2, "0")
        results[year + month] = get_top_pages_by_date(year, month, 0)
        print(f"Completed: {month}/{year}")
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    generate_monthly()
