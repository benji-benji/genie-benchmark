"""filter Genie to the probes a given model can actually surface.

the free-text rungs have no gold continuation — they are scored by reading what the
model wrote. a probe that cannot surface target_old BEFORE any edit could never have
shown propagation after one, so its result is noise. this pass measures which probes
can fire, per model.

model-dependent, unlike everything in genie_bench/: run once per model, before the
eval. follows RippleEdits' filter_benchmark_by_model.py — the filtered benchmark is
a separate artefact per model, and the surfacing rate is itself a reported result.

--stratify CATEGORY keeps only records that still hold a probe of that category after
filtering. abstract_3 survives on ~6% of records, so a random n=100 would measure it about
six times; stratifying on it buys ~100 measurements for the same GPU cost. the other rungs
then describe that stratum rather than the whole table, which has to be said in the report.

run: uv run python -m genie_bench.scripts.genie_filter_by_model --model gpt2-xl [--limit N] [--drop-unsurfaced]
     uv run python -m genie_bench.scripts.genie_filter_by_model --model gpt2-xl --drop-unsurfaced --stratify abstract_3
"""
import argparse, collections, json, re, torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer

from genie_bench.filtering import filter_records, stratify

ROOT = Path(__file__).resolve().parents[2]   # genie_bench/scripts/x.py -> repo root
GENIE = ROOT / "data" / "raw" / "genie" / "genie.json"
TABLE = ROOT / "artifacts" / "bench_generation" / "genie_table.json"

RUNGS = ("abstract_2", "abstract_3")
MAX_NEW_TOKENS = 20        # RippleEdits-style 20-token generation protocol
BATCH = 16

def pick_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def mentions(text, answers) -> bool:
    "is any accepted answer present as a whole word (case-insensitive)?"
    return any(
        re.search(rf"(?<!\w){re.escape(a)}(?!\w)", text, re.IGNORECASE)
        for a in (answers or ()) if a
    )


def generate(model, tok, prompts):
    "greedy continuations, left-padded so each completion starts at its prompt's end"
    tok.padding_side = "left"          # right padding would generate from pad tokens
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    out = []
    for i in range(0, len(prompts), BATCH):
        enc = tok(prompts[i:i + BATCH], return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=MAX_NEW_TOKENS,
                                 do_sample=False, pad_token_id=tok.eos_token_id)
        out += [tok.decode(g[enc["input_ids"].shape[1]:], skip_special_tokens=True)
                for g in gen]
        print(f"  generated {min(i + BATCH, len(prompts))}/{len(prompts)}", end="\r")
    return out

def measure(model, tok, records):
    "one surfacing record per free-text probe"
    jobs = [(r, p) for r in records for p in r["probes"] if p["category"] in RUNGS]
    print(f"{len(jobs)} free-text probes over {len(records)} records")

    texts = generate(model, tok, [p["prompt"] for _, p in jobs])
    return [
        {
            "case_id": r["case_id"],
            "category": p["category"],
            "relation": r["relation"],
            "frame": r["meta"]["frame"],
            "sitelinks": r["meta"].get("sitelinks"),
            "surfaced": mentions(text, p["answer_old"]),
            "text": text.strip(),
        }
        for (r, p), text in zip(jobs, texts)
    ]
    
def report(surfacing):
    "surfacing rate per rung, and against subject prominence — the 2b question"
    for rung in RUNGS:
        rows = [s for s in surfacing if s["category"] == rung]
        if not rows:
            continue
        hit = sum(s["surfaced"] for s in rows)
        print(f"\n{rung}: {hit}/{len(rows)} surfaced ({100 * hit / len(rows):.0f}%)")

        bands = [(0, 37), (37, 62), (62, 99), (99, 189), (189, 10**6)]
        for lo, hi in bands:
            b = [s for s in rows if s["sitelinks"] is not None and lo <= s["sitelinks"] < hi]
            if b:
                h = sum(s["surfaced"] for s in b)
                print(f"   sitelinks {lo:3}-{hi if hi < 10**6 else '+':<4} "
                      f"n={len(b):3}  surfaced {h:3} ({100 * h / len(b):3.0f}%)")
                

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="short name used in output files, e.g. gpt2-xl")
    ap.add_argument("--model-path", default=None,
                    help="local path or Hugging Face id; defaults to ./models/<model>")
    ap.add_argument("--limit", type=int, default=None, help="first N records, for a trial run")
    ap.add_argument("--drop-unsurfaced", action="store_true",
                    help="prune probes that never surfaced. off by default: measure first")
    ap.add_argument("--stratify", metavar="CATEGORY", default=None,
                    help="keep only records still holding this category, e.g. abstract_3")
    args = ap.parse_args()

    records = json.loads(GENIE.read_text())
    if args.limit:
        records = records[:args.limit]

    device = pick_device()
    print(f"loading {args.model} on {device}")
    path = args.model_path or f"./models/{args.model}"
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path).to(device).eval()

    surfacing = measure(model, tok, records)

    out_dir = ROOT / "artifacts" / "bench_generation"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"genie_surfacing_{args.model}.json").write_text(
        json.dumps(surfacing, indent=2, ensure_ascii=False))

    report(surfacing)

    kept = filter_records(records, surfacing) if args.drop_unsurfaced else records
    if args.stratify:
        before = len(kept)
        kept = stratify(kept, args.stratify)
        print(f"\nstratified on {args.stratify}: {len(kept)}/{before} records kept")
    dest = GENIE.parent / f"genie_{args.model}.json"
    dest.write_text(json.dumps(kept, indent=2, ensure_ascii=False))

    n_probes = sum(len(r["probes"]) for r in kept)
    verb = "filtered" if args.drop_unsurfaced else "unfiltered copy"
    verb += f", stratified on {args.stratify}" if args.stratify else ""
    print(f"\n{len(kept)} records, {n_probes} probes ({verb}) -> {dest}")
    # the per-category n the results table needs: composition is ragged, because a maker
    # only emits a probe when the table row supports it.
    counts = collections.Counter(p["category"] for r in kept for p in r["probes"])
    for cat, n in sorted(counts.items()):
        print(f"  {cat:<14} {n:6}   {100 * n / len(kept):5.1f}% of records")


if __name__ == "__main__":
    main()
