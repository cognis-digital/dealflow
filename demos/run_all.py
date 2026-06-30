"""Run every demo scenario end to end.

    python demos/run_all.py

Each scenario is independent and loads its own bundled sample pipeline YAML +
deal-log CSV from this repo, then drives the real dealflow API offline. They can
be run in any order or on their own.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCENARIOS = [
    "01_founder_forecast",
    "02_revops_funnel",
    "03_bd_rep_deals",
    "04_finance_ci_gate",
    "05_analyst_csv_export",
]


def main() -> None:
    for name in SCENARIOS:
        mod = importlib.import_module(name)
        mod.main()
    print("\n" + "=" * 70)
    print("  All demo scenarios completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
