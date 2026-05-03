"""Smoke tests for DEALFLOW — import core, run on the demo, assert real behavior."""
import json
import os
import subprocess
import sys

import pytest

from dealflow import core, TOOL_NAME, TOOL_VERSION
from dealflow.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "demos", "01-basic")
PIPELINE = os.path.join(DEMO, "pipeline.yml")
DEALS = os.path.join(DEMO, "deals.csv")


def _report():
    pipe = core.load_pipeline(PIPELINE)
    deals = core.load_deals(DEALS)
    return pipe, deals, core.analyze(pipe, deals)


def test_metadata():
    assert TOOL_NAME == "dealflow"
    assert TOOL_VERSION.count(".") == 2


def test_pipeline_parse():
    pipe = core.load_pipeline(PIPELINE)
    assert pipe.name == "B2B Sales"
    assert [s.name for s in pipe.stages] == ["lead", "qualified", "proposal", "won", "lost"]
    assert pipe.won_stage == "won"
    assert "lost" in pipe.lost_stages
    assert [s.name for s in pipe.open_stages] == ["lead", "qualified", "proposal"]


def test_deal_loading():
    deals = core.load_deals(DEALS)
    assert len(deals) == 6
    d1 = next(d for d in deals if d.deal_id == "D1")
    assert d1.amount == 30000
    assert d1.current_stage == "won"
    # history sorted chronologically
    dates = [d for _, d in d1.history]
    assert dates == sorted(dates)


def test_counts_and_winrate():
    _, _, rep = _report()
    assert rep.total_deals == 6
    assert rep.won_deals == 2
    assert rep.lost_deals == 1
    assert rep.open_deals == 3
    # decided win rate = 2 / 3
    assert round(rep.overall_win_rate, 4) == round(2 / 3, 4)
    assert rep.won_value == 80000


def test_advance_rates_and_velocity():
    _, _, rep = _report()
    by = {s["stage"]: s for s in rep.stages}
    # All 6 deals entered lead; 5 advanced to qualified.
    assert by["lead"]["entered"] == 6
    assert by["lead"]["advanced"] == 5
    assert by["lead"]["advance_rate"] == round(5 / 6, 4)
    # proposal: 3 entered (D1,D2,D3), 2 advanced to won
    assert by["proposal"]["entered"] == 3
    assert by["proposal"]["advanced"] == 2
    # velocity present and positive for stages deals left
    assert by["lead"]["avg_days_in_stage"] is not None
    assert by["lead"]["avg_days_in_stage"] > 0
    # terminal stages have no advance rate
    assert by["won"]["advance_rate"] is None


def test_weighted_forecast_is_risk_adjusted():
    _, _, rep = _report()
    # forecast positive but strictly below the raw open pipeline value
    assert rep.weighted_forecast > 0
    assert rep.weighted_forecast < rep.open_value
    # won deals contribute 0 to the open forecast
    won_rows = [d for d in rep.deals if d["status"] == "won"]
    assert all(d["expected_value"] == 0.0 for d in won_rows)
    # lost deals have p_win 0
    lost_rows = [d for d in rep.deals if d["status"] == "lost"]
    assert all(d["p_win"] == 0.0 for d in lost_rows)


def test_p_win_monotonic_along_pipeline():
    _, _, rep = _report()
    by = {s["stage"]: s for s in rep.stages}
    # later open stages should have >= probability of winning
    assert by["lead"]["p_win"] <= by["qualified"]["p_win"] <= by["proposal"]["p_win"]
    assert by["won"]["p_win"] == 1.0


def test_unknown_stage_raises():
    pipe = core.load_pipeline(PIPELINE)
    bad = core.load_deals("deal_id,stage,date,amount\nX,nope,2026-01-01,100\n", is_text=True)
    with pytest.raises(core.DealflowError):
        core.analyze(pipe, bad)


def test_cli_json_and_exit_codes(capsys):
    rc = main(["forecast", "-p", PIPELINE, "-d", DEALS, "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["total_deals"] == 6
    assert data["won_deals"] == 2
    assert "weighted_forecast" in data


def test_cli_gate_fails(capsys):
    # Absurdly high forecast floor -> gate fails -> non-zero exit.
    rc = main(["forecast", "-p", PIPELINE, "-d", DEALS, "--min-forecast", "100000000"])
    assert rc == 1


def test_cli_gate_passes():
    rc = main(["forecast", "-p", PIPELINE, "-d", DEALS, "--min-forecast", "1"])
    assert rc == 0


def test_module_entrypoint_runs():
    proc = subprocess.run(
        [sys.executable, "-m", "dealflow", "forecast", "-p", PIPELINE, "-d", DEALS],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "Weighted forecast" in proc.stdout
