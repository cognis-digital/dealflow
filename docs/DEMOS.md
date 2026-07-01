# Demos

Two flavors of demo ship in [`../demos/`](../demos/):

1. **Narrated Python scenarios** — `NN_name.py` scripts, each written for a
   different audience, that drive the **real** dealflow API offline against a
   bundled sample pipeline and print a clear, narrated story. They double as
   smoke tests: each exits `0`.
2. **Data scenarios** — `NN-name/` directories (pipeline.yml + deals.csv +
   SCENARIO.md) you can run straight through the CLI.

```bash
PYTHONUTF8=1 python demos/run_all.py            # all narrated scenarios
PYTHONUTF8=1 python demos/02_revops_funnel.py   # or just one

# the data scenarios go through the CLI:
python -m dealflow forecast -p demos/02-saas-monthly/pipeline.yml \
                            -d demos/02-saas-monthly/deals.csv
```

## Narrated scenarios — by audience

| # | Scenario | Audience | What it shows | Sample data |
|---|----------|----------|---------------|-------------|
| 1 | [`01_founder_forecast.py`](../demos/01_founder_forecast.py) | Founders / sales leaders | Raw open pipeline vs. risk-adjusted weighted forecast, and the haircut between them — the board number, reproducible from git | `01-basic` (B2B Sales) |
| 2 | [`02_revops_funnel.py`](../demos/02_revops_funnel.py) | RevOps / sales ops | Per-stage advance rate + velocity to pinpoint the leak (worst conversion) and the bottleneck (slowest stage) | `02-saas-monthly` (SaaS New Business) |
| 3 | [`03_bd_rep_deals.py`](../demos/03_bd_rep_deals.py) | BD reps / AEs | A worklist of open deals ranked by expected value, plus the oldest (stalled) deals to chase or disqualify | `03-enterprise-longcycle` (Enterprise Field Sales) |
| 4 | [`04_finance_ci_gate.py`](../demos/04_finance_ci_gate.py) | Finance / forecasting | The CLI as a CI tripwire: a realistic `--min-forecast` gate passes (exit 0), an over-target gate fails the build (exit 1) | `05-quarterly-gate` (Q3 Commit) |
| 5 | [`05_analyst_csv_export.py`](../demos/05_analyst_csv_export.py) | Data analysts / BI | `--format csv` per-deal export, parsed back and reconciled against the engine forecast to prove it's clean, computable data | `08-csv-export-bi` (Partner Channel) |
| 6 | [`06_stalled_deals.py`](../demos/06_stalled_deals.py) | Sales managers | Open deals ranked by `age_days` to find what has stalled and needs chasing or disqualifying | `06-stalled-deals` |
| 7 | [`07_minimal_noamount.py`](../demos/07_minimal_noamount.py) | Community / free-tier ops | Conversion + velocity with **no amount column** — the dollar forecast is `$0` but the funnel math is real | `07-minimal-noamount` |
| 8 | [`08_mixed_dateformats.py`](../demos/08_mixed_dateformats.py) | Ops merging exports | Multiple date formats and `"$45,000"`-style money in one file, normalized by the loader | `09-mixed-dateformats` |
| 9 | [`09_json_pipeline_api.py`](../demos/09_json_pipeline_api.py) | Platform / integrations | `Report.to_dict()` as machine-readable JSON with the invariants a consumer can trust | `02-saas-monthly` |
| 10 | [`10_flow_mapping_yaml.py`](../demos/10_flow_mapping_yaml.py) | Anyone writing pipelines | Inline flow-mapping YAML (`- {name: x, type: y}`) builds the same state machine as block style | `10-flow-mapping` |
| 11 | [`11_zero_win_quarter.py`](../demos/11_zero_win_quarter.py) | Skeptical finance | The honest `$0`: a zero-win history forecasts nothing instead of inventing value or crashing | `14-all-lost` |
| 12 | [`12_enterprise_acv.py`](../demos/12_enterprise_acv.py) | Enterprise sales | Seven-figure deals with formatted money and per-deal expected-value contribution | `12-quoted-amounts` |
| 13 | [`13_plg_velocity.py`](../demos/13_plg_velocity.py) | PLG / growth | Velocity measured in days on a fast self-serve funnel | `13-fast-velocity` |
| 14 | [`14_partial_amounts.py`](../demos/14_partial_amounts.py) | RevOps with messy CRM | Deals with missing amounts still count for conversion; missing = `$0` value | `15-partial-amounts` |
| 15 | [`15_large_pipeline_scale.py`](../demos/15_large_pipeline_scale.py) | Skeptics / QA | 60 deals through 5 open stages, asserting the engine's invariants hold at volume | `16-large-pipeline` |
| 16 | [`16_error_handling.py`](../demos/16_error_handling.py) | Integrators | Each malformed input (bad pipeline, unknown stage, bad date, negative amount, missing column) raises a precise `DealflowError` | inline |
| 17 | [`17_winrate_gate.py`](../demos/17_winrate_gate.py) | Finance / CI | The `--min-win-rate` gate fails a build on eroding quality, independent of the dollar forecast | `02-saas-monthly` |

Each narrated scenario rebuilds its result from a bundled sample, so they run in
any order or on their own, fully offline. `tests/` covers the same code paths
under `pytest`.

## Data scenarios

| Demo | Scenario |
|------|----------|
| [`01-basic`](../demos/01-basic/) | 5-stage B2B forecast — the canonical walkthrough |
| [`02-saas-monthly`](../demos/02-saas-monthly/) | SaaS funnel with a procurement/legal stage where deals stall |
| [`03-enterprise-longcycle`](../demos/03-enterprise-longcycle/) | Enterprise field sales, long cycles, two loss reasons |
| [`04-inbound-velocity`](../demos/04-inbound-velocity/) | High-volume self-serve funnel — velocity in days |
| [`05-quarterly-gate`](../demos/05-quarterly-gate/) | Fail CI when the quarterly weighted forecast drops below target |
| [`06-stalled-deals`](../demos/06-stalled-deals/) | Surface aging/stalled deals via the `age_days` column |
| [`07-minimal-noamount`](../demos/07-minimal-noamount/) | Smallest input: string stages, no amounts → conversion-only |
| [`08-csv-export-bi`](../demos/08-csv-export-bi/) | `--format csv` per-deal export for spreadsheets / BI |
| [`09-mixed-dateformats`](../demos/09-mixed-dateformats/) | Mixed date & `$1,200`-style currency formats |
| [`10-flow-mapping`](../demos/10-flow-mapping/) | Pipeline written with inline YAML flow mappings |
| [`11-single-stage`](../demos/11-single-stage/) | Degenerate one-stage pipeline (boundary case) |
| [`12-quoted-amounts`](../demos/12-quoted-amounts/) | Seven-figure `"$1,250,000"`-formatted enterprise amounts |
| [`13-fast-velocity`](../demos/13-fast-velocity/) | Product-led-growth funnel converting in days |
| [`14-all-lost`](../demos/14-all-lost/) | Zero-win quarter → honest `$0` forecast |
| [`15-partial-amounts`](../demos/15-partial-amounts/) | Mixed log where some deals lack an amount |
| [`16-large-pipeline`](../demos/16-large-pipeline/) | 60 deals through a 5-open-stage wide funnel |
