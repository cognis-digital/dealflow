# Demo 03 — Enterprise field sales, long cycle, two loss reasons

An enterprise field-sales team runs 4–6 month cycles through a buying
committee. They track **two distinct loss reasons** (`lost_no_decision` vs
`lost_competitor`) as separate terminal stages so the forecast can tell
"we got out-sold" apart from "the deal died of inertia".

## Data

- `pipeline.yml` — `sourced -> discovery -> solution_review -> business_case ->
  contracting -> won`, plus two lost terminals.
- `deals.csv` — 8 large deals ($95k–$500k) spanning Sep 2025 → Feb 2026.

## Run

```sh
python -m dealflow forecast -p demos/03-enterprise-longcycle/pipeline.yml \
                            -d demos/03-enterprise-longcycle/deals.csv
```

## What you should see

- **8 deals · 5 open · 1 won · 2 lost · 33.3% decided win rate.**
- `avg_days_in_stage` is 28–40 days per stage — this is the long-cycle
  signature; the velocity column is the headline metric here.
- Open pipeline value **$1,590,000**, weighted forecast **~$555,491**.

## How to act

Two losses on three decided deals is a thin win rate; both loss terminals
contribute, but only one is competitive. The single deal in `contracting`
(ENT-5003, $420k) carries roughly half its value as expected value because the
late-stage advance rates are favourable. Forecast both loss reasons separately
by reading the JSON stage rows:

```sh
python -m dealflow forecast -p demos/03-enterprise-longcycle/pipeline.yml \
                            -d demos/03-enterprise-longcycle/deals.csv \
                            --format json | jq '.stages[] | select(.won==false and .terminal==true)'
```
