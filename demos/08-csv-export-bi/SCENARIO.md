# Demo 08 — CSV export for spreadsheets / BI

Showcases the `--format csv` exporter (added alongside `table` and `json`). It
emits **one row per deal** with the columns a spreadsheet or BI tool wants:
`deal_id, current_stage, status, amount, p_win, expected_value, age_days`.
Drop it straight into Sheets/Excel, a `LOAD DATA` import, or a CRM bulk update.

## Data

- `pipeline.yml` — a partner-channel pipeline `registered -> qualified ->
  proposal -> closed_won`, plus `closed_lost`.
- `deals.csv` — 7 channel deals.

## Run

```sh
python -m dealflow forecast -p demos/08-csv-export-bi/pipeline.yml \
                            -d demos/08-csv-export-bi/deals.csv --format csv
```

## What you should see

A CSV like:

```csv
deal_id,current_stage,status,amount,p_win,expected_value,age_days
CH-7001,closed_won,won,28000.0,1.0,0.0,56
CH-7002,proposal,open,52000.0,0.5,26000.0,35
CH-7003,closed_lost,lost,19000.0,0.0,0.0,35
...
```

- `expected_value` = `amount * p_win` for open deals (0 for won/lost), so the
  column sums to the weighted forecast.
- 7 deals · 4 open · 2 won · 1 lost.

## How to act

Write it to a file and import it anywhere:

```sh
python -m dealflow forecast -p demos/08-csv-export-bi/pipeline.yml \
                            -d demos/08-csv-export-bi/deals.csv --format csv > forecast.csv
```

`forecast.csv` is a deterministic artifact — commit it next to the pipeline so
diffs show exactly how the forecast moved week over week.
