# Demo 05 — Quarterly forecast gate in CI

This demo treats the **weighted forecast as a build artifact**. A scheduled CI
job re-runs `dealflow` against the latest CRM export and **fails the build** if
the risk-adjusted forecast falls below the quarterly target — so RevOps finds
out the quarter is at risk from a red pipeline, not from a Friday surprise.

## Data

- `pipeline.yml` — a compact commit pipeline: `commit -> best_case ->
  closed_won`, plus a `slipped` terminal.
- `deals.csv` — 6 deals for Q3 2026.

## Run (report)

```sh
python -m dealflow forecast -p demos/05-quarterly-gate/pipeline.yml \
                            -d demos/05-quarterly-gate/deals.csv
```

Weighted forecast for this dataset is **$67,500**.

## The gate

```sh
# Quarter is healthy — passes (exit 0):
python -m dealflow forecast -p demos/05-quarterly-gate/pipeline.yml \
                            -d demos/05-quarterly-gate/deals.csv --min-forecast 50000
echo "exit: $?"      # -> 0

# Quarter target is $250k — gate FAILS (exit 1):
python -m dealflow forecast -p demos/05-quarterly-gate/pipeline.yml \
                            -d demos/05-quarterly-gate/deals.csv --min-forecast 250000
echo "exit: $?"      # -> 1
```

## How to act

Drop the gate into a GitHub Action on a cron and on every CRM-export commit.
A non-zero exit blocks the merge / pages the on-call RevOps owner. Combine with
`--min-win-rate` to also guard against a forecast that only looks healthy
because of a few oversized, low-probability deals.
