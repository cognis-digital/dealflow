"""Tests for the narrated demo scenarios.

Each demo drives the real dealflow API offline against a bundled sample. These
tests import every scenario's main(), run it, and assert it completes cleanly
and prints its narration — so the demos double as smoke tests under pytest.
"""
import importlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")
sys.path.insert(0, DEMOS)

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
    "18_concentration_risk",
]


@pytest.mark.parametrize("name", SCENARIOS)
def test_demo_runs_and_narrates(name, capsys):
    mod = importlib.import_module(name)
    # main() must not raise (the CI-gate demo asserts its own exit codes).
    mod.main()
    out = capsys.readouterr().out
    assert out.strip(), f"{name} printed nothing"
    # every scenario draws a titled rule via _common.rule()
    assert "=" * 70 in out


def test_common_helpers_use_real_api():
    common = importlib.import_module("_common")
    pipeline, rep = common.load("01-basic")
    # values must match the real engine (and the README example)
    assert pipeline.name == "B2B Sales"
    assert rep.total_deals == 6
    assert round(rep.weighted_forecast, 2) == 27666.67
    by = common.by_stage(rep)
    assert set(by) == {"lead", "qualified", "proposal", "won", "lost"}


def test_run_all_exits_zero(capsys):
    run_all = importlib.import_module("run_all")
    run_all.main()  # raises on any failure
    out = capsys.readouterr().out
    assert "All demo scenarios completed." in out


def test_finance_gate_demo_exercises_both_exit_codes():
    demo = importlib.import_module("04_finance_ci_gate")
    pipe, deals = demo.sample("05-quarterly-gate")
    base = ["forecast", "-p", pipe, "-d", deals, "--format", "json"]
    assert demo._quiet_gate(base, 50_000) == 0    # realistic floor passes
    assert demo._quiet_gate(base, 100_000) == 1   # over-target floor fails
