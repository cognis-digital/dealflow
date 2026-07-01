"""Tests for the bundled demo DATA scenarios (NN-name/ directories).

These lock in the expected counts/forecasts for every data scenario and assert
the cross-cutting invariants hold on each: advanced<=entered, P(win) monotone,
and sum(open expected_value) reconciles to the weighted forecast.
"""
import os

import pytest

from dealflow.core import analyze, load_deals, load_pipeline
from dealflow.cli import main, _render_csv
import csv
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")

ALL_DATA_DEMOS = [
    "01-basic", "02-saas-monthly", "03-enterprise-longcycle", "04-inbound-velocity",
    "05-quarterly-gate", "06-stalled-deals", "07-minimal-noamount", "08-csv-export-bi",
    "09-mixed-dateformats", "10-flow-mapping", "11-single-stage", "12-quoted-amounts",
    "13-fast-velocity", "14-all-lost", "15-partial-amounts", "16-large-pipeline",
]

# (demo, total, open, won, lost) for the NEW scenarios
NEW_CASES = [
    ("10-flow-mapping", 5, 2, 2, 1),
    ("11-single-stage", 3, 0, 3, 0),
    ("12-quoted-amounts", 4, 2, 1, 1),
    ("13-fast-velocity", 7, 3, 3, 1),
    ("14-all-lost", 4, 1, 0, 3),
    ("15-partial-amounts", 5, 2, 2, 1),
    ("16-large-pipeline", 60, 50, 8, 2),
]


def rep(demo):
    p = os.path.join(DEMOS, demo, "pipeline.yml")
    d = os.path.join(DEMOS, demo, "deals.csv")
    return analyze(load_pipeline(p), load_deals(d))


@pytest.mark.parametrize("demo,total,opn,won,lost", NEW_CASES)
def test_new_demo_counts(demo, total, opn, won, lost):
    r = rep(demo)
    assert (r.total_deals, r.open_deals, r.won_deals, r.lost_deals) == (total, opn, won, lost)


@pytest.mark.parametrize("demo,total,opn,won,lost", NEW_CASES)
def test_new_demo_cli_exits_zero(demo, total, opn, won, lost, capsys):
    p = os.path.join(DEMOS, demo, "pipeline.yml")
    d = os.path.join(DEMOS, demo, "deals.csv")
    assert main(["forecast", "-p", p, "-d", d]) == 0
    capsys.readouterr()


@pytest.mark.parametrize("demo", ALL_DATA_DEMOS)
def test_every_demo_loads_and_analyzes(demo):
    r = rep(demo)
    assert r.total_deals >= 1
    assert r.total_deals == r.open_deals + r.won_deals + r.lost_deals


@pytest.mark.parametrize("demo", ALL_DATA_DEMOS)
def test_advanced_never_exceeds_entered(demo):
    for s in rep(demo).stages:
        assert s["advanced"] <= s["entered"]


@pytest.mark.parametrize("demo", ALL_DATA_DEMOS)
def test_pwin_non_decreasing_along_open_stages(demo):
    r = rep(demo)
    open_stages = [s for s in r.stages if not s["terminal"]]
    prev = -1.0
    for s in open_stages:
        assert s["p_win"] + 1e-9 >= prev
        prev = s["p_win"]


@pytest.mark.parametrize("demo", ALL_DATA_DEMOS)
def test_forecast_reconciles_to_open_expected_values(demo):
    r = rep(demo)
    ev = sum(d["expected_value"] for d in r.deals if d["status"] == "open")
    assert abs(ev - r.weighted_forecast) < 0.5


@pytest.mark.parametrize("demo", ALL_DATA_DEMOS)
def test_win_rate_in_unit_interval(demo):
    assert 0.0 <= rep(demo).overall_win_rate <= 1.0


@pytest.mark.parametrize("demo", ALL_DATA_DEMOS)
def test_csv_export_row_per_deal(demo):
    r = rep(demo)
    rows = list(csv.DictReader(io.StringIO(_render_csv(r))))
    assert len(rows) == r.total_deals


# --------------------------------------------------------------------------- #
# targeted numbers for a few new scenarios
# --------------------------------------------------------------------------- #
def test_flow_mapping_equivalent_forecast():
    r = rep("10-flow-mapping")
    assert round(r.weighted_forecast, 2) == 30000.0
    assert r.won_value == 70000.0


def test_quoted_amounts_parsed():
    r = rep("12-quoted-amounts")
    assert r.won_value == 1_250_000.0
    assert r.open_value == 1_250_000.0  # Q2 (800k) + Q3 (450k)


def test_all_lost_forecasts_zero():
    r = rep("14-all-lost")
    assert r.weighted_forecast == 0.0
    assert r.won_deals == 0


def test_partial_amounts_still_count_deals():
    r = rep("15-partial-amounts")
    # P2 (won, blank amount) contributes 0 to won_value but is counted won.
    assert r.won_deals == 2
    assert r.won_value == 5000.0  # only P1 carried an amount


def test_single_stage_all_won_no_open_value():
    r = rep("11-single-stage")
    assert r.won_deals == 3 and r.open_deals == 0
    assert r.open_value == 0.0
