# 15 — Partial / missing amounts

The amount column exists but some rows leave it blank. DEALFLOW treats a
missing amount as `$0` value while still counting the deal for conversion and
velocity. So a rep who forgot to fill in the deal size doesn't vanish from the
funnel math — they just contribute nothing to the dollar forecast.

Run:

    dealflow forecast -p demos/15-partial-amounts/pipeline.yml -d demos/15-partial-amounts/deals.csv
