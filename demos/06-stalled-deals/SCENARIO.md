# Demo 06 — Finding stalled / aging deals

A renewals & expansion team wants to surface deals that have **gone quiet**.
DEALFLOW reports an `age_days` per deal (calendar days from first to last
recorded event) — sort on it to find deals that have sat untouched.

## Data

- `pipeline.yml` — `identified -> engaged -> negotiation -> renewed`, plus
  `lost`.
- `deals.csv` — 7 accounts. Several were last touched in late 2025 and have
  not moved since.

## Run

```sh
python -m dealflow forecast -p demos/06-stalled-deals/pipeline.yml \
                            -d demos/06-stalled-deals/deals.csv --format csv
```

## What you should see

- **7 deals · 4 open · 2 won · 1 lost · 66.7% decided win rate.**
- In the CSV, `REN-301` and `REN-307` (both open, in `negotiation`) show the
  largest `age_days` (42) — these are the stalled deals to chase first.
- Weighted forecast **~$129,833** against **$290,000** of open pipeline.

## How to act

Pipe the CSV through `sort` to get a worklist ordered by staleness:

```sh
python -m dealflow forecast -p demos/06-stalled-deals/pipeline.yml \
                            -d demos/06-stalled-deals/deals.csv --format csv \
  | tail -n +2 | awk -F, '$3=="open"' | sort -t, -k7 -nr
```

The oldest open rows are your re-engagement list. A deal still in `negotiation`
after months is a forecast risk even though its `P(WIN)` looks healthy — its
age, not its stage, is the warning sign.
