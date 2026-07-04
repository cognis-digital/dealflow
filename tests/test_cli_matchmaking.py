"""CLI tests for the matchmaking / teaming / pipeline / report subcommands."""
import json
import os

import pytest

from dealflow.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MM = os.path.join(ROOT, "demos", "matchmaking")
COMPANY = os.path.join(MM, "company.yml")
OPP = os.path.join(MM, "opportunity.yml")
ROSTER = os.path.join(MM, "roster.yml")
PIPE = os.path.join(MM, "pipeline.yml")


# --------------------------------------------------------------------------- #
# match
# --------------------------------------------------------------------------- #
def test_match_table(capsys):
    assert main(["match", "-c", COMPANY]) == 0
    out = capsys.readouterr().out
    assert "Capital matches for: Aperture Sensing" in out
    assert "SBIR" in out


def test_match_json(capsys):
    assert main(["match", "-c", COMPANY, "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["matches"]
    assert "factors" in data["matches"][0]
    assert data["matches"][0]["score"] >= data["matches"][-1]["score"]


def test_match_csv(capsys):
    assert main(["match", "-c", COMPANY, "--format", "csv"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("company,source,score")


def test_match_top_limits(capsys):
    assert main(["match", "-c", COMPANY, "--format", "json", "--top", "2"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["matches"]) == 2


def test_match_explain(capsys):
    assert main(["match", "-c", COMPANY, "--top", "1", "--explain"]) == 0
    out = capsys.readouterr().out
    assert "factors:" in out


def test_match_weights_override(capsys):
    assert main(["match", "-c", COMPANY, "--weights", "sector=3", "--format", "json"]) == 0
    json.loads(capsys.readouterr().out)  # still valid


def test_match_missing_company_returns_2(capsys):
    assert main(["match", "-c", "nope.yml"]) == 2
    assert "error:" in capsys.readouterr().err


def test_match_bad_weights_returns_2(capsys):
    assert main(["match", "-c", COMPANY, "--weights", "sector=notanum"]) == 2
    assert "error:" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# sources
# --------------------------------------------------------------------------- #
def test_sources_table(capsys):
    assert main(["sources"]) == 0
    out = capsys.readouterr().out
    assert "Capital sources" in out
    assert "sbir-phase-i" in out


def test_sources_category_filter(capsys):
    assert main(["sources", "--category", "equity-vc", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert all(s["category"] == "equity-vc" for s in data["sources"])


def test_sources_by_id(capsys):
    assert main(["sources", "--id", "ota-prototype", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 1
    assert data["sources"][0]["id"] == "ota-prototype"


def test_sources_unknown_id_returns_2(capsys):
    assert main(["sources", "--id", "ghost"]) == 2


# --------------------------------------------------------------------------- #
# team
# --------------------------------------------------------------------------- #
def test_team_table(capsys):
    assert main(["team", "-o", OPP, "-r", ROSTER]) == 0
    out = capsys.readouterr().out
    assert "Teaming recommendation" in out
    assert "coverage" in out.lower()


def test_team_json_complete(capsys):
    assert main(["team", "-o", OPP, "-r", ROSTER, "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["coverage"] == 1.0
    assert data["complete"] is True


def test_team_forced_prime(capsys):
    assert main(["team", "-o", OPP, "-r", ROSTER, "--prime", "cybersb", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["prime"] == "cybersb"


def test_team_require_complete_gate_passes(capsys):
    assert main(["team", "-o", OPP, "-r", ROSTER, "--require-complete"]) == 0
    capsys.readouterr()


def test_team_require_complete_gate_fails(tmp_path, capsys):
    thin = tmp_path / "roster.yml"
    thin.write_text("- id: p\n  name: P\n  capabilities: [radar]\n", encoding="utf-8")
    rc = main(["team", "-o", OPP, "-r", str(thin), "--require-complete"])
    assert rc == 1
    assert "gate:" in capsys.readouterr().err


def test_team_max_members(capsys):
    assert main(["team", "-o", OPP, "-r", ROSTER, "--max-members", "1", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["members"]) == 1


# --------------------------------------------------------------------------- #
# pipeline
# --------------------------------------------------------------------------- #
def test_pipeline_table(capsys):
    assert main(["pipeline", "-f", PIPE]) == 0
    out = capsys.readouterr().out
    assert "Opportunity pipeline" in out
    assert "Weighted pipeline" in out
    assert "Next actions" in out


def test_pipeline_json(capsys):
    assert main(["pipeline", "-f", PIPE, "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total_opportunities"] == 5
    assert "weighted_pipeline" in data


def test_pipeline_open_only(capsys):
    assert main(["pipeline", "-f", PIPE, "--open-only", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert all(o["status"] == "open" for o in data["opportunities"])


def test_pipeline_min_weighted_gate_fails(capsys):
    rc = main(["pipeline", "-f", PIPE, "--min-weighted", "1e12"])
    assert rc == 1
    assert "gate:" in capsys.readouterr().err


def test_pipeline_min_weighted_gate_passes(capsys):
    assert main(["pipeline", "-f", PIPE, "--min-weighted", "1"]) == 0
    capsys.readouterr()


def test_pipeline_missing_file_returns_2(capsys):
    assert main(["pipeline", "-f", "nope.yml"]) == 2


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def test_report_match_html_stdout(capsys):
    assert main(["report", "match", "-c", COMPANY, "--top", "3"]) == 0
    out = capsys.readouterr().out
    assert out.lstrip().startswith("<!doctype html>")
    assert "<script" not in out.lower()


def test_report_match_writes_file(tmp_path, capsys):
    out = tmp_path / "match.html"
    assert main(["report", "match", "-c", COMPANY, "-o", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Capital match report" in text
    assert "https://" not in text


def test_report_match_csv(capsys):
    assert main(["report", "match", "-c", COMPANY, "--format", "csv"]) == 0
    assert "company,source,score" in capsys.readouterr().out


def test_report_team_html(tmp_path):
    out = tmp_path / "team.html"
    assert main(["report", "team", "-o", OPP, "-r", ROSTER, "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Teaming brief" in text
    assert "<script" not in text.lower()


def test_report_team_json(capsys):
    assert main(["report", "team", "-o", OPP, "-r", ROSTER, "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["opportunity"]


def test_report_no_kind_returns_2():
    with pytest.raises(SystemExit):
        main(["report"])
