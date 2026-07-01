# 12 — Quoted / formatted money amounts

Real CRM exports rarely give you clean numbers. This log writes amounts as
`"$1,250,000"` — quoted, with a currency symbol and thousands separators.
DEALFLOW strips the `$` and commas and parses the value, so a seven-figure
enterprise pipeline forecasts correctly without pre-cleaning the export.

Run:

    dealflow forecast -p demos/12-quoted-amounts/pipeline.yml -d demos/12-quoted-amounts/deals.csv
