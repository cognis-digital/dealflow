"""Tests for the strategic-teaming graph + recommender (dealflow.teaming)."""
import pytest

from dealflow.core import DealflowError
from dealflow.teaming import (
    SET_ASIDES,
    Opportunity,
    Org,
    TeamingGraph,
    gap_analysis,
    recommend_team,
)


def _roster():
    return [
        {"id": "prime", "name": "PrimeCo", "role": "prime",
         "capabilities": ["systems-integration", "radar"], "past_performance": ["dod"]},
        {"id": "ai", "name": "EdgeAI", "role": "small-business",
         "capabilities": ["edge-ai"], "set_asides": ["sdvosb"]},
        {"id": "cyber", "name": "CyberSB", "role": "small-business",
         "capabilities": ["cybersecurity"], "set_asides": ["8(a)"]},
        {"id": "logi", "name": "LogiCo", "role": "sub", "capabilities": ["logistics"]},
    ]


def _opp():
    return Opportunity.from_dict({
        "name": "C-UAS",
        "required": ["radar", "edge-ai", "systems-integration", "cybersecurity"],
        "preferred": ["logistics"],
        "set_aside_goals": ["sdvosb", "8(a)"],
    })


# --------------------------------------------------------------------------- #
# model construction
# --------------------------------------------------------------------------- #
def test_org_from_dict_normalizes():
    o = Org.from_dict({"name": "X", "capabilities": ["A", "b"], "set_asides": "SDVOSB"})
    assert o.id == "X"
    assert o.capabilities == {"a", "b"}
    assert o.set_asides == {"sdvosb"}


def test_org_requires_id_or_name():
    with pytest.raises(DealflowError):
        Org.from_dict({"capabilities": ["x"]})


def test_org_caps_flow_sequence_string():
    o = Org.from_dict({"name": "X", "capabilities": "[radar, edge-ai]"})
    assert o.capabilities == {"radar", "edge-ai"}


def test_graph_rejects_duplicate_ids():
    with pytest.raises(DealflowError):
        TeamingGraph.from_dicts([{"id": "a"}, {"id": "a"}])


def test_graph_get_by_id_and_name():
    g = TeamingGraph.from_dicts(_roster())
    assert g.get("prime").name == "PrimeCo"
    assert g.get("PrimeCo").id == "prime"


def test_graph_get_unknown_raises():
    with pytest.raises(DealflowError):
        TeamingGraph.from_dicts(_roster()).get("ghost")


def test_set_asides_vocabulary_present():
    assert "8(a)" in SET_ASIDES and "sdvosb" in SET_ASIDES


# --------------------------------------------------------------------------- #
# complementary edges
# --------------------------------------------------------------------------- #
def test_complements_returns_new_capabilities():
    g = TeamingGraph.from_dicts(_roster())
    comps = g.complements("prime")
    # every complement brings capabilities the prime lacks
    for org, new in comps:
        assert new and new <= org.capabilities
        assert not (new & g.get("prime").capabilities)


def test_edges_are_deduplicated_and_scored():
    g = TeamingGraph.from_dicts(_roster())
    edges = g.edges()
    pairs = {tuple(sorted((e["a"], e["b"]))) for e in edges}
    assert len(pairs) == len(edges)  # no duplicate undirected pairs
    assert all(e["complementarity"] >= 1 for e in edges)


# --------------------------------------------------------------------------- #
# gap analysis
# --------------------------------------------------------------------------- #
def test_gap_analysis_full_and_partial():
    g = TeamingGraph.from_dicts(_roster())
    opp = _opp()
    ga_prime = gap_analysis([g.get("prime")], opp)
    assert "edge-ai" in ga_prime["uncovered"]
    assert ga_prime["coverage"] < 1.0
    full = [g.get(x) for x in ("prime", "ai", "cyber")]
    ga_full = gap_analysis(full, opp)
    assert ga_full["uncovered"] == set()
    assert ga_full["coverage"] == 1.0
    assert ga_full["set_asides_met"] == {"sdvosb", "8(a)"}


def test_gap_analysis_no_requirements_is_full_coverage():
    opp = Opportunity(name="empty")
    assert gap_analysis([], opp)["coverage"] == 1.0


# --------------------------------------------------------------------------- #
# recommender
# --------------------------------------------------------------------------- #
def test_recommend_team_covers_all_requirements():
    g = TeamingGraph.from_dicts(_roster())
    rec = recommend_team(g, _opp())
    assert rec.coverage == 1.0
    assert rec.uncovered == set()
    assert rec.set_asides_missing == set()
    assert rec.prime == "prime"
    assert set(rec.members) >= {"prime", "ai", "cyber"}


def test_recommend_team_is_deterministic():
    g = TeamingGraph.from_dicts(_roster())
    a = recommend_team(g, _opp()).members
    b = recommend_team(g, _opp()).members
    assert a == b


def test_recommend_team_honors_forced_prime():
    g = TeamingGraph.from_dicts(_roster())
    rec = recommend_team(g, _opp(), prime="cyber")
    assert rec.prime == "cyber"
    assert rec.members[0] == "cyber"


def test_recommend_team_respects_max_members():
    g = TeamingGraph.from_dicts(_roster())
    rec = recommend_team(g, _opp(), max_members=2)
    assert len(rec.members) <= 2
    # with only 2 members it cannot cover everything here
    assert rec.uncovered or rec.set_asides_missing


def test_recommend_reports_gaps_when_capability_absent():
    roster = [{"id": "p", "name": "P", "capabilities": ["radar"]}]
    g = TeamingGraph.from_dicts(roster)
    rec = recommend_team(g, _opp())
    assert "edge-ai" in rec.uncovered
    assert rec.to_dict()["complete"] is False


def test_empty_graph_raises():
    with pytest.raises(DealflowError):
        recommend_team(TeamingGraph(orgs=[]), _opp())


def test_recommendation_to_dict_shape():
    g = TeamingGraph.from_dicts(_roster())
    d = recommend_team(g, _opp()).to_dict()
    for k in ("opportunity", "prime", "members", "covered", "uncovered",
              "coverage", "complete", "rationale"):
        assert k in d
    assert d["complete"] is True
    assert isinstance(d["rationale"], list) and d["rationale"]
