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
    "06_stalled_deals",
    "07_minimal_noamount",
    "08_mixed_dateformats",
    "09_json_pipeline_api",
    "10_flow_mapping_yaml",
    "11_zero_win_quarter",
    "12_enterprise_acv",
    "13_plg_velocity",
    "14_partial_amounts",
    "15_large_pipeline_scale",
    "16_error_handling",
    "17_winrate_gate",
    # capital-matchmaking + strategic-teaming engine
    "19_capital_matchmaking",
    "20_growth_stage_matching",
    "21_capital_source_taxonomy",
    "22_strategic_teaming",
    "23_teaming_gap_analysis",
    "24_capture_pipeline",
    "25_match_report_html",
    "26_teaming_graph_edges",
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
