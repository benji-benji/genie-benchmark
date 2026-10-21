

import json
import re
from pathlib import Path

from genie_bench.genie_hardcode import (
    ABSTRACT_1,
    ABSTRACT_2,
    ABSTRACT_2_PERSON,
    ABSTRACT_3,
    ABSTRACT_3_MIN_SITELINKS,
    ABSTRACT_3_PERSON,
    FRAMES,
    HOP,
    HOP_NAMES,
    PARAPHRASES,
    RELATION_DISPLAY,
)
from genie_bench.ripple_relations import Ripple_Relation

HUMAN = "Q5"
PARENS = re.compile(r"\s*\([^)]*\)")
ARTICLE = re.compile(r"^(The|A|An)\s+")


ROOT = Path(__file__).resolve().parents[2]   # genie_bench/scripts/x.py -> repo root
TABLE_PATH = ROOT / "artifacts" / "bench_generation" / "genie_table.json"
OUT_PATH = ROOT / "data" / "raw" / "genie" / "genie.json"

RELATION_BY_PID = {r.id(): r for r in Ripple_Relation if r.id()}

PEOPLE_BY_SUBJECT = {}


def build_person_index(rows):
    PEOPLE_BY_SUBJECT.clear()
    for r in rows:
        o = r["object"]
        if o.get("gender_qid") and o.get("label") and (o.get("sitelinks") or 0) > 0:
            PEOPLE_BY_SUBJECT.setdefault(r["subject"]["label"], []).append(
                {"label": o["label"], "sitelinks": o["sitelinks"],
                 "pid": r["relation"]["pid"]})
    return PEOPLE_BY_SUBJECT


def associated_person(row):
    edited_pid = row["relation"]["pid"]
    candidates = [c for c in PEOPLE_BY_SUBJECT.get(row["subject"]["label"], [])
                  if c["pid"] != edited_pid]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c["sitelinks"])["label"]


class GenieRecord:

    def __init__(self, row, index):
        relation = RELATION_BY_PID[row["relation"]["pid"]]
        self.case_id = f"{row['relation']['name'].replace(' ', '_')}_{index}"
        self.subject = row["subject"]["label"]
        self.relation = row["relation"]["name"]
        self.prompt = relation.phrase("{}")  # keeps {} so construct_prompt() works
        self.target_old = row["object"]["label"]
        self.target_new = row["alt"]["label"]
        self.meta = {"pid": row["relation"]["pid"],
                "frame": row["subject"]["discursive_frame"],
                "year": row["subject"]["year"],
                "location": row["subject"].get("location"),
                "sitelinks": row["subject"].get("sitelinks")}
        self.probes = build_probes(row)

    def get_json(self):
        return {
            "case_id": self.case_id,
            "subject": self.subject,
            "relation": self.relation,
            "prompt": self.prompt,
            "target_old": self.target_old,
            "target_new": self.target_new,
            "meta": self.meta,
            "probes": self.probes,
        }

    def __repr__(self):
        return f"GenieRecord({self.case_id!r}, {self.subject!r}, probes={len(self.probes)})"


def plural(word):

    if len(word) > 1 and word.endswith("y") and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def probe(category, prompt, row, old=None, new=None, constraints=None):
    out = {
        "category": category,
        "prompt": prompt,
        "answer_old": old or [row["object"]["label"]],
        "answer_new": new or [row["alt"]["label"]],
    }
    # which narrowing devices this prompt actually used. Recorded rather than split into
    # separate categories so n stays intact and the surfacing rate per constraint can be
    # reported post hoc.
    if constraints is not None:
        out["constraints"] = constraints
    return out


def variants(label, subject, is_person):
    bare = PARENS.sub("", label).strip()
    out = [label, bare, ARTICLE.sub("", bare)]

    if " for " in bare:
        out.append(bare.split(" for ")[0])  # "X Award for Best Y" -> "X Award"
    if is_person and len(bare.split()) >= 2:
        out.append(bare.split()[-1])  # surname, people only

    seen, keep = set(), []
    for v in (x.strip() for x in out):
        if len(v) < 4 or v.lower() in seen:
            continue
        if v.lower() in subject.lower():  # never match the subject's own name
            continue
        seen.add(v.lower())
        keep.append(v)
    return keep


def display(row):
    name = row["relation"]["name"]
    return RELATION_DISPLAY.get(name, name)


def efficacy(row):
    return probe(
        "efficacy",
        RELATION_BY_PID[row["relation"]["pid"]].phrase(row["subject"]["label"]),
        row,
    )


def paraphrases(row):
    frame = row["subject"]["discursive_frame"]
    rel = RELATION_DISPLAY.get(row["relation"]["name"], row["relation"]["name"])
    out = []
    for n, band in enumerate(("PARAPHRASE_1", "PARAPHRASE_2", "PARAPHRASE_3"), start=1):
        tmpl = PARAPHRASES[band].get(frame) if frame else None
        if not tmpl:
            continue
        out.append(
            probe(
                f"paraphrase_{n}",
                tmpl.format(
                    subject=row["subject"]["label"],
                    subject_class=row["subject"]["class"],
                    relation=rel,
                ),
                row,
            )
        )
    return out


def hops(row):
    o, a = row["object"]["hops"], row["alt"]["hops"]
    out = []
    for n in range(min(len(o), len(a))):
        if o[n]["pid"] != a[n]["pid"] or o[n]["label"] == a[n]["label"]:
            break  # different property, or the same answer both sides
        chain = " of the ".join(HOP_NAMES[h["pid"]] for h in reversed(o[: n + 1]))
        out.append(
            probe(
                f"hop_{n + 1}",
                HOP.format(
                    chain=chain, relation=display(row), subject=row["subject"]["label"]
                ),
                row,
                [o[n]["label"]],
                [a[n]["label"]],
            )
        )
    return out


def abstract_1(row):
    old, new = row["object"].get("comparator"), row["alt"].get("comparator")
    if not (old and new):
        return None  # one-to-one relations have no comparator
    a, b = sorted([old, new])  # alphabetical, so position never signals the answer
    return probe(
        "abstract_1",
        ABSTRACT_1.format(
            a=a, b=b, relation=display(row), subject=row["subject"]["label"]
        ),
        row,
        [old],
        [new],
    )


def abstract_2(row):
    frame = row["subject"]["discursive_frame"]
    # FRAMES lags the table: scaling the seed set surfaces relations that were never
    # sampled before. skip rather than raise — probes are ragged by design.
    if not frame or frame not in ABSTRACT_2 or row["relation"]["name"] not in FRAMES:
        return None
    person = row["object"].get("class_qid") == HUMAN
    subject = row["subject"]["label"]
    old = variants(row["object"]["label"], subject, person)
    new = variants(row["alt"]["label"], subject, person)
    if not old or not new:
        return None          # every term collided with the subject's own name
    person_label = associated_person(row)
    template = ABSTRACT_2_PERSON[frame] if person_label else ABSTRACT_2[frame]
    return probe(
        "abstract_2",
        template.format(
            frame=FRAMES[row["relation"]["name"]],
            subject=subject,
            subject_class=row["subject"]["class"],
            year=row["subject"]["year"],
            person=person_label,
        ),
        row,
        old,
        new,
        constraints=["subject"] + (["person"] if person_label else []),
    )


def abstract_3(row):
    frame = row["subject"]["discursive_frame"]
    if (not frame or frame not in ABSTRACT_3 or not row["subject"].get("class")
            or row["relation"]["name"] not in FRAMES):
        return None
    # prominence gate: an obscure subject will never be named however the class is
    # phrased, so gating removes noise rather than signal. See ABSTRACT_3_MIN_SITELINKS.
    if (row["subject"].get("sitelinks") or 0) < ABSTRACT_3_MIN_SITELINKS:
        return None
    person = row["object"].get("class_qid") == HUMAN
    subject = row["subject"]["label"]
    old = variants(row["object"]["label"], subject, person)
    new = variants(row["alt"]["label"], subject, person)
    if not old or not new:
        return None
    person_label = associated_person(row)
    template = ABSTRACT_3_PERSON[frame] if person_label else ABSTRACT_3[frame]
    return probe(
        "abstract_3",
        template.format(
            frame=FRAMES[row["relation"]["name"]],
            subject_class=plural(row["subject"]["class"]),
            year=row["subject"]["year"],
            person=person_label,
        ),
        row,
        old,
        new,
        constraints=(["year"] if row["subject"].get("year") else [])
                    + (["person"] if person_label else []),
    )


MAKERS = [efficacy, paraphrases, hops, abstract_1, abstract_2, abstract_3]


def build_probes(row):
    out = []
    for make in MAKERS:
        got = make(row)
        out += got if isinstance(got, list) else [got]
    return [p for p in out if p]


def main():
    rows = json.loads(TABLE_PATH.read_text())
    # must precede GenieRecord: the makers read PEOPLE_BY_SUBJECT
    build_person_index(rows)
    records = [GenieRecord(row, i) for i, row in enumerate(rows)]

    counts = {}
    for rec in records:
        for p in rec.probes:
            counts[p["category"]] = counts.get(p["category"], 0) + 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps([r.get_json() for r in records], indent=2, ensure_ascii=False)
    )
    print(f"{len(records)} records, {sum(counts.values())} probes -> {OUT_PATH}")
    for c, n in sorted(counts.items()):
        print(f"  {c:16} {n}")


if __name__ == "__main__":
    main()
