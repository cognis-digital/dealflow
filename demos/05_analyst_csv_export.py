"""Scenario 5 - Data analysts / BI.

The forecast shouldn't be trapped in a CLI. Analysts want per-deal rows they can
drop into a spreadsheet, a BI tool, or a CRM bulk-import. dealflow's `--format
csv` emits exactly that: one row per deal with status, P(win), expected value,
and age. This demo drives the real CSV renderer and parses its output back to
prove it's well-formed, computable data — not a screenshot.
"""
import csv
import io

from _common import money, rule, sample

from dealflow.cli import _render_csv
from dealflow.core import analyze, load_deals, load_pipeline


def main() -> None:
    rule("ANALYST / BI EXPORT  -  per-deal rows for the spreadsheet")
    pipe, deals = sample("08-csv-export-bi")

    rep = analyze(load_pipeline(pipe), load_deals(deals))
    csv_text = _render_csv(rep)

    print(f"\nPipeline: {rep.pipeline}   ({rep.total_deals} deals)\n")
    print("Raw `--format csv` output (the real renderer):")
    for line in csv_text.splitlines()[:6]:
        print(f"  {line}")
    if rep.total_deals > 5:
        print(f"  ... ({rep.total_deals - 5} more rows)")

    # Parse it back — proving downstream tools can consume it directly.
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(rows) == rep.total_deals

    open_rows = [r for r in rows if r["status"] == "open"]
    pipeline_ev = sum(float(r["expected_value"]) for r in open_rows)

    print("\nWhat a BI tool computes from these rows in one GROUP BY:")
    print(f"  rows parsed cleanly      : {len(rows)} (== deals on file)")
    print(f"  open deals               : {len(open_rows)}")
    print(f"  sum(expected_value) open : {money(pipeline_ev)}")
    print(f"  matches engine forecast  : {money(rep.weighted_forecast)} "
          f"({'YES' if round(pipeline_ev, 2) == round(rep.weighted_forecast, 2) else 'NO'})")

    print("\nPipe it straight to a file for Sheets / Looker / a CRM import:")
    print("    dealflow forecast -p pipeline.yml -d deals.csv --format csv > forecast.csv")


if __name__ == "__main__":
    main()
