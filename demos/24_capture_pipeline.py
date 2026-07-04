"""24 · Capture pipeline — probability-weighted value + next-action prompts.

Audience: a BD / capture lead running a portfolio of pursuits.

Loads a pipeline of opportunities (capital raises, contract pursuits), rolls up
probability-weighted value, flags stale pursuits that have gone quiet, and emits
a stage-driven next-action prompt for each open opportunity.

Offline. Exit 0.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.opps import parse_tracker                        # noqa: E402
from demos._common import money, rule                          # noqa: E402

PIPELINE = """
stale_days: 30
opportunities:
  - id: o1
    name: Navy sensing OTA
    stage: proposal
    value: 4000000
    updated: 2026-06-01
  - id: o2
    name: SBIR Phase II award
    stage: submitted
    value: 1800000
    updated: 2026-06-25
  - id: o3
    name: Army C2 recompete
    stage: capture
    value: 12000000
    updated: 2026-01-10
  - id: o4
    name: Air Force pitch day
    stage: qualified
    value: 900000
    updated: 2026-06-20
  - id: o5
    name: Prior lost bid
    stage: lost
    value: 500000
"""


def main() -> None:
    rule("24 · Capture pipeline — the weighted forecast + what to do next")

    tracker = parse_tracker(PIPELINE)
    today = dt.date(2026, 7, 1)          # fixed "today" so the demo is deterministic
    summary = tracker.summary(today=today)

    print(f"Pipeline: {summary['total_opportunities']} opportunities "
          f"({summary['open']} open · {summary['won']} won · {summary['lost']} lost)")
    print(f"  Open value        : {money(summary['open_value'])}")
    print(f"  Weighted pipeline : {money(summary['weighted_pipeline'])}\n")

    print(f"  {'OPPORTUNITY':<24}{'STAGE':<12}{'VALUE':>12}{'P':>6}{'WEIGHTED':>13}")
    print("  " + "-" * 66)
    for r in summary["opportunities"]:
        flag = "*" if r["stale"] else " "
        print(f"{flag} {r['name'][:22]:<24}{r['stage']:<12}{money(r['value']):>12}"
              f"{r['probability'] * 100:>5.0f}%{money(r['weighted_value']):>13}")

    print("\nNext actions (open pursuits):")
    for r in summary["opportunities"]:
        if r["status"] == "open":
            print(f"  - [{r['name']}] {r['next_action']}")

    stale = [r for r in summary["opportunities"] if r["stale"]]
    print(f"\n{len(stale)} pursuit(s) flagged stale (no update > {tracker.stale_days}d) — "
          "chase them before they slip.")


if __name__ == "__main__":
    main()
