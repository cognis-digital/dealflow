"""Tests for self-contained HTML/CSV/JSON reports (dealflow.reports)."""
import csv
import io
import json
import re

from dealflow.matching import rank_matches, score_match
from dealflow.capital_sources import default_catalog
from dealflow.teaming import Opportunity, TeamingGraph, recommend_team
from dealflow.reports import (
    match_report_html,
    matches_csv,
    matches_json,
    team_json,
    teaming_brief_html,
)


def _matches():
    company = {"name": "Aperture", "stage": "seed", "ask": 1_500_000,
               "sectors": ["dual-use"], "dual_use": "dual-use"}
    return company["name"], rank_matches(company, default_catalog().sources, top=3)


def _team():
    roster = [
        {"id": "prime", "name": "PrimeCo", "role": "prime",
         "capabilities": ["radar", "systems-integration"]},
        {"id": "ai", "name": "EdgeAI", "capabilities": ["edge-ai"], "set_asides": ["sdvosb"]},
    ]
    opp = Opportunity.from_dict({
        "name": "C-UAS", "required": ["radar", "edge-ai", "systems-integration"],
        "set_aside_goals": ["sdvosb"],
    })
    g = TeamingGraph.from_dicts(roster)
    return opp, g, recommend_team(g, opp)


# --------------------------------------------------------------------------- #
# HTML self-containment (no JS, no external assets)
# --------------------------------------------------------------------------- #
def _assert_self_contained(html_text: str):
    assert html_text.lstrip().startswith("<!doctype html>")
    assert "<script" not in html_text.lower()
    # no external references of any kind
    assert "http://" not in html_text and "https://" not in html_text
    assert "src=" not in html_text
    assert "cdn" not in html_text.lower()


def test_match_report_is_self_contained():
    name, matches = _matches()
    html_text = match_report_html(name, matches)
    _assert_self_contained(html_text)
    assert "Capital match report" in html_text
    assert name in html_text
    for m in matches:
        assert m.source in html_text


def test_teaming_brief_is_self_contained():
    opp, g, rec = _team()
    orgs = {o.id: o for o in g.orgs}
    html_text = teaming_brief_html(rec, opp, orgs)
    _assert_self_contained(html_text)
    assert "Teaming brief" in html_text
    assert "PrimeCo" in html_text


def test_html_escapes_untrusted_fields():
    company = {"name": "<script>alert(1)</script>", "stage": "seed"}
    matches = rank_matches(company, default_catalog().sources, top=1)
    html_text = match_report_html(company["name"], matches)
    assert "<script>alert(1)</script>" not in html_text
    assert "&lt;script&gt;" in html_text


def test_match_report_shows_factor_percentages():
    name, matches = _matches()
    html_text = match_report_html(name, matches)
    assert re.search(r"\d+%", html_text)  # factor match percentages rendered
    assert "abstained" in html_text or "%" in html_text


# --------------------------------------------------------------------------- #
# CSV / JSON export
# --------------------------------------------------------------------------- #
def test_matches_csv_parses():
    _, matches = _matches()
    rows = list(csv.DictReader(io.StringIO(matches_csv(matches))))
    assert len(rows) == len(matches)
    assert set(rows[0]) == {"company", "source", "score", "band", "top_factors"}


def test_matches_json_valid():
    _, matches = _matches()
    data = json.loads(matches_json(matches))
    assert len(data["matches"]) == len(matches)
    assert "factors" in data["matches"][0]


def test_team_json_valid():
    _, _, rec = _team()
    data = json.loads(team_json(rec))
    assert data["opportunity"] == "C-UAS"
    assert data["complete"] is True


def test_empty_matches_report():
    html_text = match_report_html("Nobody", [])
    _assert_self_contained(html_text)
    assert "No matches" in html_text
