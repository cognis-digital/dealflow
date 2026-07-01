"""CLI tests: output formats, exit codes, gates, error handling, --version."""
import csv
import io
import json
import os
import subprocess
import sys

import pytest

from dealflow import TOOL_VERSION
from dealflow.cli import main, _render_csv, _render_table, _fmt_money
from dealflow.core import analyze, load_deals, load_pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")
BASIC_P = os.path.join(DEMOS, "01-basic", "pipeline.yml")
BASIC_D = os.path.join(DEMOS, "01-basic", "deals.csv")


def _rep(demo="01-basic"):
    p = os.path.join(DEMOS, demo, "pipeline.yml")
    d = os.path.join(DEMOS, demo, "deals.csv")
    return analyze(load_pipeline(p), load_deals(d))


# --------------------------------------------------------------------------- #
# exit codes
# --------------------------------------------------------------------------- #
def test_no_command_prints_help_and_returns_2(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_forecast_success_returns_0(capsys):
    assert main(["forecast", "-p", BASIC_P, "-d", BASIC_D]) == 0
    capsys.readouterr()


def test_missing_pipeline_file_returns_2(capsys):
    rc = main(["forecast", "-p", "nope.yml", "-d", BASIC_D])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_missing_deals_file_returns_2(capsys):
    rc = main(["forecast", "-p", BASIC_P, "-d", "nope.csv"])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_malformed_pipeline_returns_2(tmp_path, capsys):
    bad = tmp_path / "bad.yml"
    bad.write_text("name: X\n", encoding="utf-8")  # no stages
    rc = main(["forecast", "-p", str(bad), "-d", BASIC_D])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_bad_deal_data_returns_2(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("deal_id,stage,date\nA,lead,not-a-date\n", encoding="utf-8")
    rc = main(["forecast", "-p", BASIC_P, "-d", str(bad)])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #
def test_min_forecast_gate_passes(capsys):
    assert main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--min-forecast", "1"]) == 0
    capsys.readouterr()


def test_min_forecast_gate_fails(capsys):
    rc = main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--min-forecast", "1e12"])
    assert rc == 1
    assert "gate:" in capsys.readouterr().err


def test_min_win_rate_gate_passes(capsys):
    assert main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--min-win-rate", "0.1"]) == 0
    capsys.readouterr()


def test_min_win_rate_gate_fails(capsys):
    rc = main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--min-win-rate", "0.99"])
    assert rc == 1
    assert "gate:" in capsys.readouterr().err


def test_both_gates_fail_returns_1(capsys):
    rc = main([
        "forecast", "-p", BASIC_P, "-d", BASIC_D,
        "--min-forecast", "1e12", "--min-win-rate", "0.99",
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "forecast" in err and "win rate" in err


def test_gate_still_prints_report_on_failure(capsys):
    main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--min-forecast", "1e12"])
    out = capsys.readouterr().out
    assert "Weighted forecast" in out  # report printed even when gate fails


# --------------------------------------------------------------------------- #
# output formats
# --------------------------------------------------------------------------- #
def test_json_format_is_valid(capsys):
    main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["pipeline"] == "B2B Sales"
    assert data["total_deals"] == 6


def test_csv_format_parses(capsys):
    main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--format", "csv"])
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert len(rows) == 6
    assert set(rows[0]) == {
        "deal_id", "current_stage", "status",
        "amount", "p_win", "expected_value", "age_days",
    }


def test_table_format_default(capsys):
    main(["forecast", "-p", BASIC_P, "-d", BASIC_D])
    out = capsys.readouterr().out
    assert "Stage breakdown:" in out
    assert "Forecast:" in out


def test_invalid_format_rejected_by_argparse():
    with pytest.raises(SystemExit):
        main(["forecast", "-p", BASIC_P, "-d", BASIC_D, "--format", "xml"])


def test_missing_required_arg_rejected():
    with pytest.raises(SystemExit):
        main(["forecast", "-p", BASIC_P])  # no --deals


# --------------------------------------------------------------------------- #
# renderer units
# --------------------------------------------------------------------------- #
def test_fmt_money():
    assert _fmt_money(1234567) == "$1,234,567"
    assert _fmt_money(0) == "$0"


def test_render_csv_matches_deal_count():
    rep = _rep()
    rows = list(csv.DictReader(io.StringIO(_render_csv(rep))))
    assert len(rows) == rep.total_deals


def test_render_table_contains_all_stages():
    rep = _rep()
    table = _render_table(rep)
    for s in rep.stages:
        assert s["stage"] in table


# --------------------------------------------------------------------------- #
# --version and module entry point
# --------------------------------------------------------------------------- #
def test_version_flag_matches_tool_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert TOOL_VERSION in out


def test_version_is_not_the_stale_placeholder():
    # Regression: --version used to report a hard-coded 0.1.0 that didn't match
    # the VERSION file. It must now track the shipped VERSION.
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as fh:
        assert TOOL_VERSION == fh.read().strip()


def test_module_entrypoint(capsys):
    proc = subprocess.run(
        [sys.executable, "-m", "dealflow", "forecast", "-p", BASIC_P, "-d", BASIC_D],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "Weighted forecast" in proc.stdout


def test_module_entrypoint_version(capsys):
    proc = subprocess.run(
        [sys.executable, "-m", "dealflow", "--version"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert TOOL_VERSION in proc.stdout
