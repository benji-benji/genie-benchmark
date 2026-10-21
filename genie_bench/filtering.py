"""Per-model filtering of GENIE, shared by the GPU filter script and the offline export.

Copied unchanged from the MSc repo (scripts/genie_filter_by_model.py).
"""


def filter_records(records, surfacing):
    "drop probes that never surfaced; drop a record only if it loses everything"
    dead = {(s["case_id"], s["category"]) for s in surfacing if not s["surfaced"]}
    out = []
    for r in records:
        kept = [p for p in r["probes"] if (r["case_id"], p["category"]) not in dead]
        if kept:
            out.append({**r, "probes": kept})
    return out

def stratify(records, category):
    "keep only records that still hold a probe of `category` after filtering"
    return [r for r in records if any(p["category"] == category for p in r["probes"])]
