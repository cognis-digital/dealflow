"""Tests for the deal-concentration risk metric and its CI gate."""
import os

import pytest

from dealflow.cli import main
from dealflow.core import analyze, load_deals, parse_pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")

PIPE = (
    "name: P\nstages:\n  - lead\n  - qualified\n"
    "  - name: won\n    type: won\n  - name: lost\n    type: lost\n"
)


def run(csv_text, pipe_text=PIPE):
    return analyze(parse_pipeline(pipe_text), load_deals(csv_text, is_text=True))


def test_concentration_zero_when_no_forecast():
    # all deals closed -> no open forecast -> concentration 0
    rep = run(
        "deal_id,stage,date,amount\n"
        "A,lead,2026-01-01,100\nA,won,2026-02-01,100\n"
    )
    assert rep.concentration == 0.0


def test_concentration_one_when_single_open_deal():
    # one won (builds a non-zero advance rate) + one open deal -> the open deal
    # is 100% of the forecast.
    rep = run(
        "deal_id,stage,date,amount\n"
        "W,lead,2026-01-01,100\nW,qualified,2026-01-08,100\nW,won,2026-01-15,100\n"
        "O,lead,2026-01-01,500\n"
    )
    assert rep.concentration == 1.0


def test_concentration_is_max_open_ev_over_forecast():
    rep = run(
        "deal_id,stage,date,amount\n"
        "W,lead,2026-01-01,100\nW,qualified,2026-01-08,100\nW,won,2026-01-15,100\n"
        "A,lead,2026-01-01,1000\n"   # big open deal
        "B,lead,2026-01-01,100\n"    # small open deal
    )
    open_evs = [d["expected_value"] for d in rep.deals if d["status"] == "open"]
    expected = max(open_evs) / rep.weighted_forecast
    assert abs(rep.concentration - expected) < 1e-9
    assert rep.concentration > 0.5  # the whale dominates


def test_concentration_in_unit_interval():
    rep = run(
        "deal_id,stage,date,amount\n"
        "W,lead,2026-01-01,100\nW,qualified,2026-01-08,100\nW,won,2026-01-15,100\n"
        "A,lead,2026-01-01,300\nB,qualified,2026-01-01,300\n"
    )
    assert 0.0 <= rep.concentration <= 1.0


def test_concentration_in_to_dict():
    rep = run("deal_id,stage,date,amount\nA,lead,2026-01-01,100\n")
    assert "concentration" in rep.to_dict()


def test_report_default_concentration_backward_compatible():
    # Report can still be built without concentration (positional/omit) -> 0.0.
    from dealflow.core import Report
    r = Report(
        pipeline="p", total_deals=0, open_deals=0, won_deals=0, lost_deals=0,
        open_value=0.0, won_value=0.0, weighted_forecast=0.0, overall_win_rate=0.0,
        stages=[], deals=[],
    )
    assert r.concentration == 0.0


# --------------------------------------------------------------------------- #
# CLI gate
# --------------------------------------------------------------------------- #
def _files(tmp_path):
    p = tmp_path / "pipe.yml"
    p.write_text(PIPE, encoding="utf-8")
    d = tmp_path / "deals.csv"
    d.write_text(
        "deal_id,stage,date,amount\n"
        "W,lead,2026-01-01,100\nW,qualified,2026-01-08,100\nW,won,2026-01-15,100\n"
        "A,lead,2026-01-01,1000\nB,lead,2026-01-01,50\n",
        encoding="utf-8",
    )
    return str(p), str(d)


def test_max_concentration_gate_fails_when_too_concentrated(tmp_path, capsys):
    p, d = _files(tmp_path)
    rc = main(["forecast", "-p", p, "-d", d, "--max-concentration", "0.5"])
    assert rc == 1
    assert "concentration" in capsys.readouterr().err


def test_max_concentration_gate_passes_when_diverse(tmp_path, capsys):
    p, d = _files(tmp_path)
    rc = main(["forecast", "-p", p, "-d", d, "--max-concentration", "0.99"])
    assert rc == 0
    capsys.readouterr()


def test_concentration_shown_in_table(tmp_path, capsys):
    p, d = _files(tmp_path)
    main(["forecast", "-p", p, "-d", d])
    assert "concentration" in capsys.readouterr().out.lower()


def test_concentration_in_json_output(tmp_path, capsys):
    import json
    p, d = _files(tmp_path)
    main(["forecast", "-p", p, "-d", d, "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert "concentration" in data and 0.0 <= data["concentration"] <= 1.0
