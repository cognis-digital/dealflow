"""Tests for the --format csv exporter and the new demo scenarios."""
import csv
import io
import os

import pytest

from dealflow import core
from dealflow.cli import main, _render_csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")

# Demos that should run cleanly (exit 0) and their expected (open, won, lost).
DEMO_CASES = [
    ("02-saas-monthly", 10, 6, 2, 2),
    ("03-enterprise-longcycle", 8, 5, 1, 2),
    ("04-inbound-velocity", 12, 5, 4, 3),
    ("06-stalled-deals", 7, 4, 2, 1),
    ("07-minimal-noamount", 6, 3, 3, 0),
    ("08-csv-export-bi", 7, 4, 2, 1),
    ("09-mixed-dateformats", 5, 3, 1, 1),
]


def _report(demo):
    p = core.load_pipeline(os.path.join(DEMOS, demo, "pipeline.yml"))
    d = core.load_deals(os.path.join(DEMOS, demo, "deals.csv"))
    return core.analyze(p, d)


@pytest.mark.parametrize("demo,total,opn,won,lost", DEMO_CASES)
def test_demo_counts(demo, total, opn, won, lost):
    rep = _report(demo)
    assert rep.total_deals == total
    assert rep.open_deals == opn
    assert rep.won_deals == won
    assert rep.lost_deals == lost


@pytest.mark.parametrize("demo,total,opn,won,lost", DEMO_CASES)
def test_demo_cli_runs(demo, total, opn, won, lost, capsys):
    pipe = os.path.join(DEMOS, demo, "pipeline.yml")
    deals = os.path.join(DEMOS, demo, "deals.csv")
    assert main(["forecast", "-p", pipe, "-d", deals]) == 0
    capsys.readouterr()


def test_csv_export_is_valid_and_matches_forecast():
    rep = _report("08-csv-export-bi")
    text = _render_csv(rep)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == rep.total_deals
    expected_cols = {
        "deal_id", "current_stage", "status",
        "amount", "p_win", "expected_value", "age_days",
    }
    assert set(rows[0].keys()) == expected_cols
    # expected_value column sums to the weighted forecast (within rounding:
    # each row is rounded to cents, so the sum can differ by a few cents).
    ev_sum = sum(float(r["expected_value"]) for r in rows)
    assert abs(ev_sum - rep.weighted_forecast) < 0.05
    # won/lost rows contribute zero expected value.
    for r in rows:
        if r["status"] in ("won", "lost"):
            assert float(r["expected_value"]) == 0.0


def test_csv_format_via_cli(capsys):
    pipe = os.path.join(DEMOS, "08-csv-export-bi", "pipeline.yml")
    deals = os.path.join(DEMOS, "08-csv-export-bi", "deals.csv")
    rc = main(["forecast", "-p", pipe, "-d", deals, "--format", "csv"])
    assert rc == 0
    out = capsys.readouterr().out
    rows = list(csv.DictReader(io.StringIO(out)))
    assert len(rows) == 7
    assert rows[0]["deal_id"]


def test_quarterly_gate_demo_fails_high_floor():
    pipe = os.path.join(DEMOS, "05-quarterly-gate", "pipeline.yml")
    deals = os.path.join(DEMOS, "05-quarterly-gate", "deals.csv")
    # forecast is 135000 -> a 250k floor must fail.
    assert main(["forecast", "-p", pipe, "-d", deals, "--min-forecast", "250000"]) == 1
    # ... and a 50k floor must pass.
    assert main(["forecast", "-p", pipe, "-d", deals, "--min-forecast", "50000"]) == 0


def test_mixed_dateformats_parse_and_amounts():
    rep = _report("09-mixed-dateformats")
    # quoted "$45,000" parsed as a number; the one won deal is $45k.
    assert rep.won_value == 45000.0
    assert rep.open_value == 81250.0


def test_noamount_demo_yields_zero_value_but_real_conversion():
    rep = _report("07-minimal-noamount")
    assert rep.weighted_forecast == 0.0
    assert rep.open_value == 0.0
    by = {s["stage"]: s for s in rep.stages}
    # conversion still computed even with no amounts.
    assert by["new"]["entered"] == 6
    assert by["new"]["advance_rate"] is not None and by["new"]["advance_rate"] > 0
