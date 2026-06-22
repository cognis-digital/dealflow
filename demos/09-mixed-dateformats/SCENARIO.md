# Demo 09 — Stitching exports with mixed date & currency formats

When you concatenate CRM exports from different regions or tools, dates and
money come in inconsistent shapes. DEALFLOW's loader is tolerant: it accepts
`YYYY-MM-DD`, `YYYY/MM/DD`, and `MM/DD/YYYY` **in the same file**, and parses
amounts written with currency symbols and thousands separators (`"$45,000"`).

## Data

- `pipeline.yml` — `prospect -> meeting -> proposal -> won`, plus `lost`.
- `deals.csv` — 5 deals where each row may use a different date format and the
  `amount` column is quoted with `$` and commas.

## Run

```sh
python -m dealflow forecast -p demos/09-mixed-dateformats/pipeline.yml \
                            -d demos/09-mixed-dateformats/deals.csv
```

## What you should see

- The mixed-format dates all parse and sort chronologically — the per-stage
  `avg_days_in_stage` values (~14–21 days) prove the dates were read correctly.
- The `$45,000`-style amounts are parsed as numbers: won value **$45,000**,
  open pipeline value **$81,250**.
- **5 deals · 3 open · 1 won · 1 lost · 50% decided win rate**, weighted
  forecast **~$32,550**.

## How to act

You do not need to normalize dates or strip currency symbols before running
DEALFLOW — feed the raw concatenated export straight in. If a date format is
genuinely unrecognized, the tool exits with code `2` and names the bad value,
so a CI step fails loudly instead of silently mis-parsing.
