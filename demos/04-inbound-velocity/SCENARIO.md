# Demo 04 — Inbound self-serve velocity

A product-led, high-volume inbound funnel. Deals are cheap ($290–$1,490) and
move in **days, not months**, so velocity (`avg_days_in_stage`) is the metric
that matters most — it is a proxy for speed-to-lead and activation friction.

## Data

- `pipeline.yml` — `signup -> activated -> sales_qualified -> paid`, plus a
  terminal `churned_trial`.
- `deals.csv` — 12 trial accounts over two weeks of May 2026.

## Run

```sh
python -m dealflow forecast -p demos/04-inbound-velocity/pipeline.yml \
                            -d demos/04-inbound-velocity/deals.csv
```

## What you should see

- **12 deals · 5 open · 4 won · 3 lost · 57.1% decided win rate.**
- Stage dwell times are tiny: `signup` ~2.6 days, `activated` ~5 days. That is
  the whole point — slow activation here is measured in single-digit days.
- Weighted forecast is small in absolute dollars (**~$995**) because ASPs are
  low; this funnel is a volume game, so watch conversion %, not dollars.

## How to act

`signup -> activated` converts at ~92% but `sales_qualified -> paid` is where
the leak is. Speeding activation (the longest early dwell) lifts the whole
chain because `P(WIN)` is the product of downstream advance rates. Export the
per-deal rows to spot accounts stuck just before `paid`:

```sh
python -m dealflow forecast -p demos/04-inbound-velocity/pipeline.yml \
                            -d demos/04-inbound-velocity/deals.csv --format csv
```
