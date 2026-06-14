"""Hardening tests for DEALFLOW — edge cases, bad input, and error paths."""
from __future__ import annotations

import os
import pytest

from dealflow.core import DealflowError, Deal, parse_pipeline, load_deals, analyze
from dealflow.cli import main

_DEMO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demos", "01-basic",
)
_PIPELINE = os.path.join(_DEMO, "pipeline.yml")
_DEALS = os.path.join(_DEMO, "deals.csv")

_DUP_STAGES_YAML = """
name: Broken
stages:
  - name: lead
    type: open
  - name: lead
    type: open
  - name: won
    type: won
"""

_SIMPLE_PIPELINE_YAML = """
name: Simple
stages:
  - name: lead
    type: open
  - name: won
    type: won
"""


# ---------------------------------------------------------------------------
# parse_pipeline: duplicate stage names
# ---------------------------------------------------------------------------

def test_duplicate_stage_names_raise():
    with pytest.raises(DealflowError, match="duplicate stage name"):
        parse_pipeline(_DUP_STAGES_YAML)


# ---------------------------------------------------------------------------
# load_deals: row-number context in error messages
# ---------------------------------------------------------------------------

def test_bad_date_includes_row_number():
    csv_text = "\n".join([
        "deal_id,stage,date,amount",
        "D1,lead,NOT-A-DATE,100",
        "",
    ])
    with pytest.raises(DealflowError, match=r"row 2"):
        load_deals(csv_text, is_text=True)


def test_bad_date_on_third_row_includes_row_three():
    csv_text = "\n".join([
        "deal_id,stage,date,amount",
        "D1,lead,2026-01-01,100",
        "D2,lead,BADDATE,200",
        "",
    ])
    with pytest.raises(DealflowError, match=r"row 3"):
        load_deals(csv_text, is_text=True)


def test_empty_stage_field_raises():
    csv_text = "\n".join([
        "deal_id,stage,date,amount",
        "D1,,2026-01-01,100",
        "",
    ])
    with pytest.raises(DealflowError, match="stage is empty"):
        load_deals(csv_text, is_text=True)


# ---------------------------------------------------------------------------
# Deal.current_stage: guard against empty history
# ---------------------------------------------------------------------------

def test_deal_empty_history_raises():
    d = Deal(deal_id="X", amount=100.0, history=[])
    with pytest.raises(DealflowError, match="no history"):
        _ = d.current_stage


# ---------------------------------------------------------------------------
# CLI: --min-win-rate out of range
# ---------------------------------------------------------------------------

def test_cli_min_win_rate_above_one_returns_error(capsys):
    rc = main(["forecast", "-p", _PIPELINE, "-d", _DEALS, "--min-win-rate", "1.5"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "0 and 1" in err


def test_cli_min_win_rate_negative_returns_error(capsys):
    rc = main(["forecast", "-p", _PIPELINE, "-d", _DEALS, "--min-win-rate", "-0.1"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "0 and 1" in err


def test_cli_min_forecast_negative_returns_error(capsys):
    rc = main(["forecast", "-p", _PIPELINE, "-d", _DEALS, "--min-forecast", "-500"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "non-negative" in err


# ---------------------------------------------------------------------------
# CLI: missing file -> exit 2
# ---------------------------------------------------------------------------

def test_cli_missing_pipeline_file_exits_2(capsys):
    rc = main(["forecast", "-p", "/no/such/pipeline.yml", "-d", _DEALS])
    assert rc == 2
    err = capsys.readouterr().err
    assert "error:" in err


def test_cli_missing_deals_file_exits_2(capsys):
    rc = main(["forecast", "-p", _PIPELINE, "-d", "/no/such/deals.csv"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "error:" in err


# ---------------------------------------------------------------------------
# analyze: empty deals list is well-defined (zero totals)
# ---------------------------------------------------------------------------

def test_analyze_empty_deals():
    pipe = parse_pipeline(_SIMPLE_PIPELINE_YAML)
    rep = analyze(pipe, [])
    assert rep.total_deals == 0
    assert rep.won_deals == 0
    assert rep.open_deals == 0
    assert rep.weighted_forecast == 0.0
    assert rep.overall_win_rate == 0.0
