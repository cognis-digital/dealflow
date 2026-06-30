# Demos

Two flavors of demo ship in [`../demos/`](../demos/):

1. **Narrated Python scenarios** — `NN_name.py` scripts, each written for a
   different audience, that drive the **real** dealflow API offline against a
   bundled sample pipeline and print a clear, narrated story. They double as
   smoke tests: each exits `0`.
2. **Data scenarios** — `NN-name/` directories (pipeline.yml + deals.csv +
   SCENARIO.md) you can run straight through the CLI.

```bash
PYTHONUTF8=1 python demos/run_all.py            # all five narrated scenarios
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
