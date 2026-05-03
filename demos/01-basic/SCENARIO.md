# Demo 01 — Basic forecast

This demo shows DEALFLOW turning a **pipeline-as-code** definition plus a CSV
deal event log into a conversion / velocity / forecast artifact.

## Files

- `pipeline.yml` — a 5-stage B2B sales pipeline modeled as a state machine:
  `lead -> qualified -> proposal -> won` (open stages) with a terminal
  `lost` stage and a terminal `won` stage.
- `deals.csv` — a stage-entry event log. One row per deal per stage entered,
  with the date of entry and the deal amount.

## Run it

```sh
python -m dealflow forecast --pipeline demos/01-basic/pipeline.yml \
                            --deals    demos/01-basic/deals.csv
```

For machine output:

```sh
python -m dealflow forecast -p demos/01-basic/pipeline.yml \
                            -d demos/01-basic/deals.csv --format json
```

## What you should see

There are **6 deals**: 2 reached `won`, 1 reached `lost`, and 3 are still open
(one in `lead`, one in `qualified`, one in `proposal`).

Expected facts the demo asserts:

- `total_deals = 6`, `won_deals = 2`, `lost_deals = 1`, `open_deals = 3`.
- Win rate over **decided** deals = 2 / (2 + 1) = **66.67%**.
- `won_value = 80000` (D1 $30k + D2 $50k).
- The `proposal` stage has a high advance rate (most deals that reach proposal
  win), so the open proposal deal carries a large expected value.
- `weighted_forecast` is positive and strictly less than the raw open pipeline
  value (it is risk-adjusted by historical advance rates).

## CI gate

```sh
# Fail the build if the weighted forecast drops below $40k:
python -m dealflow forecast -p demos/01-basic/pipeline.yml \
                            -d demos/01-basic/deals.csv --min-forecast 40000
echo "exit code: $?"
```
