"""Export GENIE as JSON Lines for Hugging Face: the full set and one evaluation set per model.

No generation and no model runs.

Version 2. Per model, the MSc filter (drop probes that never surfaced pre-edit, then keep
records that still hold an abstract_3 probe) is applied to the committed surfacing results
in artifacts/. Every abstract_2 / abstract_3 probe whose prompt already contains one
of its old answers (e.g. "Akira Kurosawa films from 1950 ..." scored on "Akira Kurosawa").
abstract_1 is exempt: it names both candidates by design. Records left with no probes are
dropped, and the per-model sets are re-stratified on abstract_3.

run: uv run python -m genie_bench.scripts.genie_export
"""

import json
import re
from pathlib import Path

from genie_bench.filtering import filter_records, stratify

ROOT = Path(__file__).resolve().parents[2]   # genie_bench/scripts/x.py -> repo root
GENIE = ROOT / "data" / "raw" / "genie" / "genie.json"
SURFACING = ROOT / "artifacts" / "bench_generation"
OUT = ROOT / "data" / "hf"
MODELS = ("gpt2-xl", "llama3-8b")
STRATIFY_ON = "abstract_3"
FREE_TEXT = ("abstract_2", "abstract_3")


def answer_in_prompt(probe):
    "does the prompt already contain an old answer, as a whole word?"
    return any(
        re.search(rf"(?<!\w){re.escape(a)}(?!\w)", probe["prompt"], re.IGNORECASE)
        for a in probe["answer_old"] if a
    )


def drop_leaked(records):
    out = []
    for r in records:
        kept = [p for p in r["probes"]
                if not (p["category"] in FREE_TEXT and answer_in_prompt(p))]
        if kept:
            out.append({**r, "probes": kept})
    return out


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n = sum(len(r["probes"]) for r in records)
    print(f"{len(records):5} records {n:6} probes -> {path.relative_to(ROOT)}")


def main():
    records = json.loads(GENIE.read_text())
    sets = {"genie": records}
    for model in MODELS:
        surfacing = json.loads((SURFACING / f"genie_surfacing_{model}.json").read_text())
        sets[f"genie_{model}"] = stratify(filter_records(records, surfacing), STRATIFY_ON)

    for name, recs in sets.items():
        out = drop_leaked(recs)
        if name != "genie":
            out = stratify(out, STRATIFY_ON)
        write_jsonl(OUT / f"{name}.jsonl", out)


if __name__ == "__main__":
    main()
