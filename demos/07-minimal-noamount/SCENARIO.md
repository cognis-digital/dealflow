# Demo 07 — Minimal pipeline, no amounts (conversion-only view)

The smallest useful input. The pipeline uses **bare string stages** (no `type:`
markers) and the deal log has **no `amount` column**. With no amounts, the
dollar forecast is zero — but conversion rates and velocity still compute, which
is exactly what you want for a top-of-funnel funnel-health check.

## Data

- `pipeline.yml` — three string stages: `new`, `working`, `closed`. With no
  explicit `won`/`lost` markers, DEALFLOW treats the **last** stage (`closed`)
  as the won/terminal stage by default.
- `deals.csv` — 6 deals with only `deal_id, stage, date` (no amount).

## Run

```sh
python -m dealflow forecast -p demos/07-minimal-noamount/pipeline.yml \
                            -d demos/07-minimal-noamount/deals.csv
```

## What you should see

- **6 deals · 3 open · 3 won · 0 lost · 100% decided win rate** (every decided
  deal reached the only terminal stage, `closed`).
- Open/won/weighted **values are all $0** — there were no amounts to weight.
- The advance-rate and `avg_days_in_stage` columns are still fully populated:
  `new -> working` ~83%, `working -> closed` ~60%.

## How to act

Use this shape when you only have stage timestamps (e.g. an early CRM, or a
funnel you instrument yourself). You get the conversion and velocity diagnosis
for free; add an `amount` column later to unlock the dollar forecast.
