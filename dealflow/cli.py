"""Command-line interface for DEALFLOW.

Examples
--------
  # Forecast a pipeline from a CSV deal log
  dealflow forecast --pipeline pipeline.yml --deals deals.csv

  # Machine-readable output for CI / piping
  dealflow forecast -p pipeline.yml -d deals.csv --format json | jq .weighted_forecast

  # Fail CI when the weighted forecast falls below target (gate)
  dealflow forecast -p pipeline.yml -d deals.csv --min-forecast 100000

Exit codes
----------
  0  success and any gate passed
  1  gate failed (forecast below --min-forecast, or win-rate below --min-win-rate)
  2  usage / parse / data error
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys

from . import TOOL_NAME, TOOL_VERSION
from .core import load_pipeline, load_deals, analyze, DealflowError, Report


def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def _render_table(rep: Report) -> str:
    lines = []
    lines.append(f"Pipeline: {rep.pipeline}")
    lines.append(
        f"Deals: {rep.total_deals} total | {rep.open_deals} open | "
        f"{rep.won_deals} won | {rep.lost_deals} lost"
    )
    lines.append(f"Win rate (decided): {rep.overall_win_rate * 100:.1f}%")
    lines.append("")
    lines.append("Stage breakdown:")
    hdr = f"  {'STAGE':<16}{'ENTER':>6}{'ADV':>5}{'ADV%':>7}{'AVG_DAYS':>10}{'P(WIN)':>9}"
    lines.append(hdr)
    lines.append("  " + "-" * (len(hdr) - 2))
    for s in rep.stages:
        adv = "" if s["advance_rate"] is None else f"{s['advance_rate'] * 100:.0f}%"
        avg = "" if s["avg_days_in_stage"] is None else f"{s['avg_days_in_stage']:.1f}"
        lines.append(
            f"  {s['stage']:<16}{s['entered']:>6}{s['advanced']:>5}{adv:>7}"
            f"{avg:>10}{s['p_win'] * 100:>8.0f}%"
        )
    lines.append("")
    lines.append("Forecast:")
    lines.append(f"  Open pipeline value : {_fmt_money(rep.open_value)}")
    lines.append(f"  Won value (closed)  : {_fmt_money(rep.won_value)}")
    lines.append(f"  Weighted forecast   : {_fmt_money(rep.weighted_forecast)}")
    lines.append(
        f"  Top-deal concentration: {rep.concentration * 100:.0f}% "
        f"(share of forecast in the single largest open deal)"
    )
    return "\n".join(lines)


def _render_csv(rep: Report) -> str:
    """Emit the per-deal forecast as CSV — pipe straight into a spreadsheet,
    BI tool, or CRM bulk-import. One row per deal, header included.
    """
    cols = [
        "deal_id", "current_stage", "status",
        "amount", "p_win", "expected_value", "age_days",
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for d in rep.deals:
        w.writerow({k: d[k] for k in cols})
    return buf.getvalue().rstrip("\n")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Model a sales pipeline as a YAML state machine and compute "
            "conversion, velocity, and a weighted forecast from a CSV deal log. "
            "Pipeline-as-code: a reproducible forecast artifact for CI."
        ),
        epilog=(
            "example:\n"
            "  dealflow forecast -p pipeline.yml -d deals.csv\n"
            "  dealflow forecast -p pipeline.yml -d deals.csv --format json --min-forecast 100000\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    fc = sub.add_parser(
        "forecast",
        help="compute conversion/velocity/forecast from a pipeline + deal log",
        description="Compute stage conversion rates, velocity, and a weighted forecast.",
    )
    fc.add_argument("-p", "--pipeline", required=True, help="path to pipeline YAML file")
    fc.add_argument("-d", "--deals", required=True, help="path to deals CSV event log")
    fc.add_argument(
        "--format", choices=("table", "json", "csv"), default="table",
        help="output format: table (human), json (full report), "
             "csv (per-deal rows for spreadsheets/CRM import) (default: table)",
    )
    fc.add_argument(
        "--min-forecast", type=float, default=None,
        help="exit non-zero if weighted forecast is below this value (CI gate)",
    )
    fc.add_argument(
        "--min-win-rate", type=float, default=None,
        help="exit non-zero if win rate (0-1) is below this value (CI gate)",
    )
    fc.add_argument(
        "--max-concentration", type=float, default=None,
        help="exit non-zero if more than this fraction (0-1) of the weighted "
             "forecast rides on the single largest open deal (CI gate against a "
             "fragile, whale-dependent forecast)",
    )
    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 2

    if args.command == "forecast":
        try:
            pipeline = load_pipeline(args.pipeline)
            deals = load_deals(args.deals)
            rep = analyze(pipeline, deals)
        except DealflowError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

        if args.format == "json":
            print(json.dumps(rep.to_dict(), indent=2))
        elif args.format == "csv":
            print(_render_csv(rep))
        else:
            print(_render_table(rep))

        gate_failed = False
        if args.min_forecast is not None and rep.weighted_forecast < args.min_forecast:
            print(
                f"gate: weighted forecast {rep.weighted_forecast:.2f} "
                f"< min {args.min_forecast:.2f}",
                file=sys.stderr,
            )
            gate_failed = True
        if args.min_win_rate is not None and rep.overall_win_rate < args.min_win_rate:
            print(
                f"gate: win rate {rep.overall_win_rate:.4f} "
                f"< min {args.min_win_rate:.4f}",
                file=sys.stderr,
            )
            gate_failed = True
        if args.max_concentration is not None and rep.concentration > args.max_concentration:
            print(
                f"gate: top-deal concentration {rep.concentration:.4f} "
                f"> max {args.max_concentration:.4f}",
                file=sys.stderr,
            )
            gate_failed = True
        return 1 if gate_failed else 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
