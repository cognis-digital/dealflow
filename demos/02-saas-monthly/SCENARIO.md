# Demo 02 — SaaS new-business with a procurement stage

A mid-market SaaS team exported one quarter of new-business deals from their
CRM. Their funnel has an extra **procurement / legal** stage that many deals
sit in before closing — a common place for forecast slippage.

## Data

- `pipeline.yml` — `discovery -> demo -> pilot -> procurement -> closed_won`,
  plus a terminal `closed_lost`.
- `deals.csv` — 10 deals (ACME … JULI), one row per stage entry, ASP $12k–$90k.
  2 are `closed_won`, 2 are `closed_lost`, 6 are still open.

## Run

```sh
python -m dealflow forecast -p demos/02-saas-monthly/pipeline.yml \
                            -d demos/02-saas-monthly/deals.csv
```

## What you should see

- **10 deals · 6 open · 2 won · 2 lost · 50.0% decided win rate.**
- `procurement` shows the highest open-stage `P(WIN)` (~67%) and a ~21-day
  average dwell — that dwell time is exactly the procurement drag to watch.
- Open pipeline value **$216,000**, weighted forecast **~$87,120**.

## How to act

The biggest single open deal (JULI-2210, $90k) is still in `discovery`, so its
risk-adjusted contribution is small. Coaching effort that moves deals out of
`procurement` faster compounds, because that stage has the best conversion but
the longest dwell. Gate the team's monthly commit:

```sh
python -m dealflow forecast -p demos/02-saas-monthly/pipeline.yml \
                            -d demos/02-saas-monthly/deals.csv --min-forecast 80000
```
