---
license: cc-by-4.0
language:
- en
pretty_name: "GENIE: GENeralisation In Edits"
task_categories:
- text-generation
tags:
- model-editing
- knowledge-editing
- evaluation
- wikidata
size_categories:
- 1K<n<10K
configs:
- config_name: full
  default: true
  data_files:
  - split: test
    path: v2/genie.jsonl
- config_name: gpt2-xl
  data_files:
  - split: test
    path: v2/genie_gpt2-xl.jsonl
- config_name: llama3-8b
  data_files:
  - split: test
    path: v2/genie_llama3-8b.jsonl
- config_name: v1-full
  data_files:
  - split: test
    path: v1/genie.jsonl
- config_name: v1-gpt2-xl
  data_files:
  - split: test
    path: v1/genie_gpt2-xl.jsonl
- config_name: v1-llama3-8b
  data_files:
  - split: test
    path: v1/genie_llama3-8b.jsonl
---

# GENIE: GENeralisation In Edits

A benchmark for model editing that asks whether an edited language model can **use** a new fact, not just **recall** it.

Each case is one counterfactual edit (subject, relation, old object → new object) built from Wikidata, paired with up to ten probes that move progressively further from the edit prompt: reworded, chained through related facts, and finally abstracted so the subject is no longer named. If an edit has changed what the model knows, the new fact should surface at every rung.

Built for the MSc thesis *Model editing: capacities and limits* (Ben Bethell, Birkbeck, University of London, 2026).

- **Code and construction pipeline:** [github.com/benji-benji/genie-benchmark](https://github.com/benji-benji/genie-benchmark)
- **Thesis code:** [github.com/benji-benji/BBK-model-editing-final-report](https://github.com/benji-benji/BBK-model-editing-final-report)

## Usage

```python
from datasets import load_dataset

genie = load_dataset("benji-benji/genie", "full", split="test")          # 7,340 cases (v2)
gpt2 = load_dataset("benji-benji/genie", "gpt2-xl", split="test")        # GPT-2-XL set (v2)
thesis = load_dataset("benji-benji/genie", "v1-gpt2-xl", split="test")   # as evaluated in the thesis
```

## Configurations

v2 is recommended: it removes free-text probes whose prompt already contains the answer being tested. v1 is the data exactly as evaluated in the thesis.

| Config | Cases | Probes | Contents |
|---|---|---|---|
| `full` | 7,340 | 48,533 | Full benchmark, 43 relations (v2) |
| `gpt2-xl` | 67 | 465 | GPT-2-XL evaluation set (v2) |
| `llama3-8b` | 375 | 2,771 | LLaMA-3-8B evaluation pool (v2) |
| `v1-full` | 7,340 | 48,795 | Full benchmark, as evaluated |
| `v1-gpt2-xl` | 95 | 680 | The 95 GPT-2-XL cases evaluated in the thesis |
| `v1-llama3-8b` | 390 | 2,880 | The pool from which the thesis sampled 95 LLaMA-3-8B cases |

## Data fields

| Field | Description |
|---|---|
| `case_id` | Unique id, `<relation>_<n>` |
| `subject` | The entity being edited |
| `relation` | Wikidata relation name |
| `prompt` | Edit prompt with `{}` for the subject |
| `target_old` / `target_new` | Original object / counterfactual object |
| `meta` | Wikidata property id (`pid`), subject frame (`work`, `person`, `org`, `place`), `year`, `location`, `sitelinks` |
| `probes` | List of probes: `category`, `prompt`, `answer_old`, `answer_new` (accepted answers), optional `constraints` |

## Probe categories

| Probe | What it asks |
|---|---|
| `efficacy` | The edit prompt itself |
| `paraphrase_1`–`3` | The same question, reworded at increasing length and indirection |
| `hop_1`–`3` | A chained question about the edited object, one to three properties deep (e.g. the birthplace of the composer of *E.T.*) |
| `abstract_1` | A forced choice between two other entities: one that shares the old object, one that shares the new |
| `abstract_2` | Open generation one rung up: the subject is named, but the relation is described in more general terms |
| `abstract_3` | Open generation with the subject removed, identified only by constraints such as year and a related person |

Probe composition is ragged by design: a probe is only generated when Wikidata supports it. `abstract_2` and `abstract_3` have no gold continuation and are scored by generating 20 tokens and checking whether an accepted answer appears as a whole word.

## Construction

1. Seed subjects: the most-viewed Wikipedia pages (Wikimedia pageviews API) and notable works (Wikidata SPARQL).
2. Facts, a counterfactual object of similar era and prominence, comparators and hop chains: Wikidata.
3. Probes generated from templates per relation and subject frame.
4. Per-model sets: each model was run once, unedited, over every `abstract_2` and `abstract_3` probe. Probes that never produced the old answer are dropped, then only cases that still hold an `abstract_3` probe are kept.

## Limitations

- Counterfactual objects are chosen to be plausible (same type, similar era and prominence) but are not checked by hand.
- Templates are English only and were written for the relations and frames sampled; some relations have no `abstract_2` or `abstract_3` templates.
- The per-model sets depend on the surfacing run for that model and are not transferable to other models; rerun the filter for a new model.
- Accepted answers are Wikidata labels plus simple variants (e.g. surname only); correct answers phrased differently are scored as misses.

## Licence

CC BY 4.0. Underlying facts from Wikidata (CC0 1.0). Relation identifiers and popularity sampling adapted from [RippleEdits](https://github.com/edenbiran/RippleEdits) (MIT).

## Citation

```
Bethell, B. (2026) Model editing: capacities and limits. MSc Data Science thesis,
Birkbeck, University of London.
```
