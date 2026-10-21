

import json
import random
import time
from pathlib import Path

import requests

from genie_bench.genie_hardcode import (
    CLASS_TO_FRAME,
    CUTOFF,
    HOP_PIDS,
    PLACE_PIDS,
    RELATION_TO_FRAME,
    YEAR_PIDS,
)
from genie_bench.ripple_get_most_viewed import HEADERS, chunk
from genie_bench.ripple_relations import Ripple_Relation

ROOT = Path(__file__).resolve().parents[2]   # genie_bench/scripts/x.py -> repo root
BENCH_GEN = ROOT / "artifacts" / "bench_generation"
TOP_PATH = BENCH_GEN / "top_entities_by_views_monthly.json"
OUT_PATH = BENCH_GEN / "genie_table.json"
WIKIDATA = "https://wikidata.org/w/api.php"
WORK_PATH = BENCH_GEN / "work_entities.json"

# every enum relation that has a pid. the popular entity is always the SUBJECT:
# P57 is a claim on the film, P50 on the book, P25 on the person.
RELATIONS = {r.id(): r.formal_name() for r in Ripple_Relation if r.id()}


def fetch(qids, prop, attempts=4):
    "batched wbgetentities, 50 ids a request -> {qid: prop payload}"
    out = {}
    for batch in chunk(qids, 50):
        for attempt in range(attempts):
            try:
                r = requests.get(
                    WIKIDATA,
                    headers=HEADERS,
                    timeout=60,
                    params={
                        "format": "json",
                        "action": "wbgetentities",
                        "prop": prop,
                        "languages": "en",
                        "ids": "|".join(batch),
                    },
                )
                if r.status_code == 200:
                    out.update(
                        {
                            q: e.get(prop, {})
                            for q, e in r.json().get("entities", {}).items()
                        }
                    )
                    break
                reason = f"http {r.status_code}"
            except requests.RequestException as e:
                reason = type(e).__name__
            wait = 5 * (attempt + 1)
            print(f"    {reason}, retry {attempt + 1}/{attempts} in {wait}s")
            time.sleep(wait)
        else:
            raise RuntimeError(f"wikidata failed {attempts}x on {len(batch)} {prop}")
    return out


def value(claims, pid):
    """single value of pid, else None. multi-valued is rejected on purpose: the
    edit is false by construction only if the subject holds one true object."""
    entries = claims.get(pid, [])
    if len(entries) != 1:
        return None
    snak = entries[0].get("mainsnak", {})
    return snak["datavalue"]["value"] if snak.get("snaktype") == "value" else None


def qid(claims, *pids):
    "first pid holding a single entity value -> its qid"
    for pid in pids:
        v = value(claims, pid)
        if isinstance(v, dict) and "id" in v:
            return v["id"]
    return None


def year(claims):
    """earliest year across YEAR_PIDS, or None.

    takes all values rather than requiring one: films and books carry several
    publication dates (one per country or edition), and value() would reject
    them. the single-value rule guards the edited object, not its metadata.
    """
    years = []
    for pid in YEAR_PIDS:
        for e in claims.get(pid, []):
            snak = e.get("mainsnak", {})
            v = snak.get("datavalue", {}).get("value", {})
            if snak.get("snaktype") == "value" and "time" in v:
                years.append(int(v["time"][1:5]))
    return min(years) if years else None


def first_qid(claims, *pids):
    "first value of the first pid present, even if multi-valued — parent topic only"
    for pid in pids:
        for e in claims.get(pid, []):
            snak = e.get("mainsnak", {})
            if snak.get("snaktype") == "value":
                return snak["datavalue"]["value"].get("id")
    return None


def frame_for(class_qid, relation_name):
    return CLASS_TO_FRAME.get(class_qid) or RELATION_TO_FRAME.get(relation_name)


def build_rows(entities, claims):
    "one row per (subject, relation) surviving the cheap filters"
    rows = []
    for q, title in entities.items():
        c = claims.get(q, {})
        y = year(c)
        if y is None or y >= CUTOFF:
            continue
        subject_class = first_qid(c, "P31")
        for pid, name in RELATIONS.items():
            if obj := qid(c, pid):
                if obj == q:
                    continue  # Wikidata gives states a P17 claim pointing at themselves
                loc = qid(c, *PLACE_PIDS)
                rows.append(
                    {
                        "subject": {
                            "label": title,
                            "qid": q,
                            "year": y,
                            "class_qid": subject_class,
                            "discursive_frame": frame_for(subject_class, name),
                            "location_qid": None if loc == q else loc,
                        },
                        "relation": {"name": name, "pid": pid},
                        "object": {"qid": obj},
                        "alt": {},
                    }
                )
    return rows


def same_era(a, b, years=25):
    return bool(a["year"] and b["year"] and abs(a["year"] - b["year"]) <= years)


def similar_fame(a, b, factor=4):
    "within a factor of each other in sitelink count — GPT-2 only knows famous things"
    x, y = a["sitelinks"], b["sitelinks"]
    return bool(x and y and max(x, y) <= min(x, y) * factor)


def add_alt_objects(rows, rng):
    """alt object = another row's object for the same relation. class must match —
    a cemetery must not become a city — then narrow by country, era and prominence
    so the counterfactual is one the model could plausibly hold. each narrowing
    falls back if it empties the pool, so a row is never lost to a missing field."""
    pools = {}
    for r in rows:
        pools.setdefault(r["relation"]["name"], []).append(r)
    for r in rows:
        o = r["object"]
        pool = [
            x
            for x in pools[r["relation"]["name"]]
            if x["object"]["qid"] != o["qid"]
            and x["object"]["class_qid"] == o["class_qid"]
        ]
        pool = [
            x for x in pool if x["object"]["country_qid"] == o["country_qid"]
        ] or pool
        pool = [x for x in pool if same_era(x["object"], o)] or pool
        pool = [x for x in pool if similar_fame(x["object"], o)] or pool
        pool = [x for x in pool if x["object"]["gender_qid"] == o["gender_qid"]] or pool
        r["alt"]["qid"] = rng.choice(pool)["object"]["qid"] if pool else None


def add_comparators(rows):
    """abstract-1 asks "which of X and Y has the same {relation} as {s}?" — so it
    needs two other subjects: one sharing the true object (right before the edit),
    one sharing the alt object (right after). null where the pool has no donor;
    the probe is skipped for that row."""
    by_object = {}
    for r in rows:
        by_object.setdefault((r["relation"]["name"], r["object"]["qid"]), []).append(r)

    def donor(rel, obj_qid, exclude):
        for x in by_object.get((rel, obj_qid), []):
            if x["subject"]["qid"] != exclude:
                return x["subject"]["label"]
        return None

    for r in rows:
        rel, me = r["relation"]["name"], r["subject"]["qid"]
        r["object"]["comparator"] = donor(rel, r["object"]["qid"], me)
        r["alt"]["comparator"] = donor(rel, r["alt"]["qid"], me)


def walk_hops(start_qids, steps=3):
    "qid -> [(pid, target_qid), ...]. first available pid wins; visited nodes skipped."
    chains = {q: [] for q in start_qids}
    frontier = {q: q for q in start_qids}
    seen = {q: {q} for q in start_qids}

    for _ in range(steps):
        claims = fetch(sorted(set(frontier.values())), "claims")
        nxt = {}
        for start, node in frontier.items():
            for pid in HOP_PIDS:
                target = first_qid(claims.get(node, {}), pid)
                if target and target not in seen[start]:
                    chains[start].append((pid, target))
                    seen[start].add(target)
                    nxt[start] = target
                    break
        frontier = nxt
    return chains


def main():

    months = json.loads(TOP_PATH.read_text())
    entities = {p["id"]: p["title"] for pages in months.values() for p in pages}

    if WORK_PATH.exists():
        for name, works in json.loads(WORK_PATH.read_text()).items():
            entities.update(works)

    keys = random.Random(0).sample(list(entities), len(entities))
    entities = {k: entities[k] for k in keys}

    print(f"{len(entities)} entities, {len(RELATIONS)} relations")

    rows = build_rows(entities, fetch(list(entities), "claims"))
    print(f"{len(rows)} rows after date + single-value filters")
    # object-side constraints: the object is what gets swapped, so plausibility
    # is a property of the object, not the subject
    obj_qids = sorted({r["object"]["qid"] for r in rows})
    obj_claims = fetch(obj_qids, "claims")
    obj_sites = fetch(obj_qids, "sitelinks")  # prominence = how many wikipedias
    for r in rows:
        q = r["object"]["qid"]
        c = obj_claims.get(q, {})
        r["object"]["class_qid"] = first_qid(c, "P31")
        r["object"]["country_qid"] = qid(c, "P17", "P27")
        r["object"]["year"] = year(c)
        r["object"]["sitelinks"] = len(obj_sites.get(q, {}))
        r["object"]["gender_qid"] = qid(c, "P21")

    rows = [r for r in rows if r["object"]["sitelinks"] > 0]
    print(f"{len(rows)} rows after dropping unknown objects")

    sub_qids = sorted({r["subject"]["qid"] for r in rows})
    sub_sites = fetch(sub_qids, "sitelinks")
    for r in rows:
        r["subject"]["sitelinks"] = len(sub_sites.get(r["subject"]["qid"], {}))

    add_alt_objects(rows, random.Random(0))

    add_comparators(rows)

    hops = walk_hops(
        {r[s]["qid"] for r in rows for s in ("object", "alt") if r[s].get("qid")}
    )
    for r in rows:
        for s in ("object", "alt"):
            r[s]["hops"] = [{"pid": p, "qid": q} for p, q in hops.get(r[s]["qid"], [])]

    # labels last, only for surviving qids — this is the expensive pass
    def spots(r):
        return [
            (r["subject"], "location_qid", "location"),
            (r["object"], "qid", "label"),
            (r["object"], "class_qid", "class"),
            (r["object"], "country_qid", "country"),
            (r["alt"], "qid", "label"),
            (r["subject"], "class_qid", "class"),
        ]

    needed = {d[k] for r in rows for d, k, _ in spots(r) if d.get(k)}
    needed |= {h["qid"] for r in rows for s in ("object", "alt") for h in r[s]["hops"]}
    labels = fetch(sorted(needed), "labels")
    for r in rows:
        for d, k, name in spots(r):
            d[name] = labels.get(d.get(k), {}).get("en", {}).get("value")
        for s in ("object", "alt"):
            for h in r[s]["hops"]:
                h["label"] = labels.get(h["qid"], {}).get("en", {}).get("value")

    rows = [r for r in rows if r["object"]["label"] and r["alt"]["label"]]
    print(f"{len(rows)} rows after dropping English labels")
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"{len(rows)} complete rows -> {OUT_PATH}")

    unmapped = {
        r["subject"]["class"]
        for r in rows
        if r["subject"]["class_qid"] not in CLASS_TO_FRAME
    }
    print(f"  classes not in CLASS_TO_FRAME: {sorted(x for x in unmapped if x)}")


if __name__ == "__main__":
    main()
