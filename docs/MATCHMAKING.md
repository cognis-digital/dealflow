# Capital matchmaking + strategic teaming

`dealflow` ships an open, self-hostable capital-matchmaking and
strategic-teaming engine — the transparent alternative to fee-based advisory
that pairs companies with funding sources and primes with subcontractors.

Everything runs **offline** (Python stdlib only), is **deterministic** (same
input → same output), and is **explainable** (scores come with a factor
breakdown, never a black box).

- [Profiles](#profiles)
- [`match` — explainable fit scoring](#match)
- [`sources` — the capital-source taxonomy](#sources)
- [`team` — strategic teaming + gap analysis](#team)
- [`pipeline` — capture pipeline tracker](#pipeline)
- [`report` — self-contained HTML/CSV/JSON](#report)
- [Python API](#python-api)
- [Scope](#scope)

Sample files live in [`demos/matchmaking/`](../demos/matchmaking/).

---

## Profiles

Every input is a plain YAML or JSON file. Fields are optional; a missing field
simply causes the relevant scoring factor to **abstain** (it is dropped from the
denominator, never counted as a zero), so a sparse profile is scored only on
what it provides.

A **company / technology profile**:

```yaml
name: Aperture Sensing
stage: seed                 # idea | pre-seed | seed | series-a | ... | public
ask: 1500000                # capital sought, USD
sectors: [dual-use, deep-tech, sensors]
technology: [edge-ai]
geography: [us]
dilution_pref: non-dilutive # non-dilutive | equity | convertible | debt | hybrid
dual_use: dual-use          # pure-defense | dual-use | commercial
trl: 4                      # technology readiness level, 1-9
keywords: [prototype, innovation, r&d]
```

---

## `match`

Rank capital sources against a company profile by transparent, weighted fit.

```bash
dealflow match -c company.yml                    # table, built-in taxonomy
dealflow match -c company.yml --explain          # + full factor breakdown
dealflow match -c company.yml --format json      # full machine-readable report
dealflow match -c company.yml --format csv       # spreadsheet-ready
dealflow match -c company.yml -s my_sources.yml  # merge your own catalog
dealflow match -c company.yml --top 5 --min-score 40
dealflow match -c company.yml --weights sector=3,stage=1   # tune the model
```

### The factors

| factor | weight | what it measures |
|---|---:|---|
| `stage` | 1.5 | company stage vs. the source's stated stages (adjacent = partial) |
| `check_size` | 1.3 | the ask vs. the source's check-size band |
| `sector` | 2.0 | Jaccard overlap of company sectors/tech vs. source thesis |
| `geography` | 0.8 | company geography inside the source's mandate |
| `mandate` | 1.2 | free-text mandate keyword overlap |
| `dilution` | 1.0 | dilution preference vs. what the source offers |
| `dual_use` | 1.1 | pure-defense / dual-use / commercial alignment |
| `readiness` | 0.7 | TRL vs. the source's minimum expected TRL |

The final score is `100 × Σ(weight × match) / Σ(weight)` over the factors that
did **not** abstain. Weights are relative and need not sum to 1. Override any of
them with `--weights name=value,...`.

Each match reports a **band**: `strong` (≥80), `promising` (≥60), `possible`
(≥40), `weak` (<40).

---

## `sources`

Browse and filter the built-in funding-vehicle taxonomy.

```bash
dealflow sources                              # all categories
dealflow sources --category equity-vc         # one category
dealflow sources --id ota-prototype --format json
dealflow sources -s my_sources.yml            # seed merged with your catalog
```

The seed catalog covers public, unclassified **categories** of vehicles — SBIR/
STTR (Phase I/II/III), OTA prototype agreements, APFIT, defense-focused VC,
strategic corporate VC, In-Q-Tel-style strategic investors, federal research
grants, project finance, growth equity, and venture debt — each with a typical
check size, dilution, timeline, minimum TRL, thesis, and a fit heuristic.

**Extend it.** A user catalog is a YAML/JSON list (or `{sources: [...]}`), keyed
by `id`. Entries with a matching `id` override the seed; new ids are added:

```yaml
- id: greenway-defense-fund
  name: Greenway Defense Fund
  category: equity-vc
  check_min: 2000000
  check_max: 15000000
  dilution: [equity]
  stages: [series-a, series-b]
  thesis: [energy, dual-use]
  dual_use: [dual-use, commercial]
  min_trl: 5
  fit: Energy-transition dual-use equity.
```

---

## `team`

Recommend a teaming arrangement for a target opportunity and run a gap analysis.

```bash
dealflow team -o opportunity.yml -r roster.yml
dealflow team -o opportunity.yml -r roster.yml --format json
dealflow team -o opportunity.yml -r roster.yml --prime primeco
dealflow team -o opportunity.yml -r roster.yml --max-members 4
dealflow team -o opportunity.yml -r roster.yml --require-complete   # CI gate
```

An **opportunity** declares required capabilities, preferred capabilities, and
set-aside goals:

```yaml
name: Counter-UAS Sensing Program
required: [radar, edge-ai, systems-integration, cybersecurity]
preferred: [logistics]
set_aside_goals: [sdvosb, 8(a)]     # 8(a) | sdvosb | vosb | hubzone | wosb | ...
```

A **roster** is a list of organizations:

```yaml
roster:
  - id: primeco
    name: PrimeCo Systems
    role: prime               # prime | sub | small-business | supplier | academic
    capabilities: [systems-integration, radar]
    set_asides: [sdvosb]
    past_performance: [dod-c2]
```

The recommender greedily assembles a team: it starts from a prime (given, or the
org covering the most required capabilities) and repeatedly adds the org with the
highest **marginal value** (new required capability, then unmet set-aside goal,
then preferred). It is deterministic — ties break on past-performance count, then
id. The output reports required-capability **coverage**, **uncovered**
requirements, **set-asides met/missing**, and a rationale for each addition.

`--require-complete` makes it a CI gate: exit non-zero if the recommended team
leaves any requirement or set-aside goal uncovered.

---

## `pipeline`

Track a capture pipeline of opportunities with probability-weighted value and
next-action prompts.

```bash
dealflow pipeline -f pipeline.yml
dealflow pipeline -f pipeline.yml --open-only
dealflow pipeline -f pipeline.yml --format json
dealflow pipeline -f pipeline.yml --min-weighted 5000000   # CI gate
```

```yaml
stale_days: 30                # flag open opps un-touched longer than this
opportunities:
  - id: o1
    name: Navy sensing OTA
    stage: proposal           # identified | qualified | capture | proposal | submitted | awarded | lost
    value: 4000000
    updated: 2026-06-01
    # probability: 0.6        # optional; overrides the stage baseline
```

Each stage carries a baseline win probability and a playbook next-action prompt
(override the whole ladder with a `stages:` block). Open opportunities whose
`updated` date is older than `stale_days` are flagged, and their next action is
prefixed `STALE (Nd, no update): ...`.

---

## `report`

Render shareable, **self-contained** artifacts — single HTML files with inline
CSS, **no JavaScript and no external/CDN assets**, so they open offline and paste
into a data room or email.

```bash
dealflow report match -c company.yml -o match_report.html
dealflow report match -c company.yml --format csv          # or json, to stdout
dealflow report team  -o opportunity.yml -r roster.yml --out teaming_brief.html
dealflow report team  -o opportunity.yml -r roster.yml --format json
```

The match report renders each source as a card with a per-factor bar chart and
its reason. The teaming brief shows the recommended team, a coverage bar, the
gap analysis, and the capture rationale.

---

## Python API

```python
from dealflow.capital_sources import default_catalog
from dealflow.matching import rank_matches, explain

company = {"name": "Aperture", "stage": "seed", "ask": 1_500_000,
           "sectors": ["dual-use", "sensors"], "dual_use": "dual-use", "trl": 4}
matches = rank_matches(company, default_catalog().sources, top=5)
print(explain(matches[0]))          # human-readable factor breakdown

from dealflow.teaming import Opportunity, TeamingGraph, recommend_team
opp = Opportunity.from_dict({"name": "X", "required": ["radar", "edge-ai"]})
graph = TeamingGraph.from_dicts([...])
rec = recommend_team(graph, opp)
print(rec.coverage, rec.uncovered)

from dealflow.opps import parse_tracker
tracker = parse_tracker(open("pipeline.yml").read())
print(tracker.summary()["weighted_pipeline"])
```

---

## Scope

This engine is deliberately scoped to **business, capital, teaming, and
market-mapping** only. It maps money and partnerships to companies. It does not
model, recommend, or touch weapons, targeting, or operational capability of any
kind. The dual-use posture and defense set-aside fields are business-classifier
metadata (who a funder or program can back), nothing more.
