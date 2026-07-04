"""Tests for the explainable capital-matchmaking engine (dealflow.matching)."""
import pytest

from dealflow.core import DealflowError
from dealflow.matching import (
    DEFAULT_FACTORS,
    FactorScore,
    MatchResult,
    _as_set,
    _norm_stage,
    explain,
    rank_matches,
    score_match,
)


# --------------------------------------------------------------------------- #
# helpers / normalization
# --------------------------------------------------------------------------- #
def test_norm_stage_aliases():
    assert _norm_stage("Series A") == "series-a"
    assert _norm_stage("preseed") == "pre-seed"
    assert _norm_stage("Pre-Seed") == "pre-seed"
    assert _norm_stage("ipo") == "public"


def test_as_set_from_list_and_string():
    assert _as_set(["A", "b", "b"]) == {"a", "b"}
    assert _as_set("x, Y ,z") == {"x", "y", "z"}
    assert _as_set(None) == set()


def test_as_set_tolerates_flow_sequence_string():
    # the minimal YAML parser hands back "[a, b, c]" verbatim
    assert _as_set("[radar, edge-ai, cyber]") == {"radar", "edge-ai", "cyber"}


# --------------------------------------------------------------------------- #
# single-match scoring
# --------------------------------------------------------------------------- #
def _perfect_source():
    return {
        "name": "Perfect Fit Fund",
        "stages": ["seed"],
        "check_min": 1_000_000,
        "check_max": 2_000_000,
        "thesis": ["dual-use", "sensors"],
        "geography": ["us"],
        "mandate": ["prototype"],
        "dilution": ["non-dilutive"],
        "dual_use": ["dual-use"],
        "min_trl": 3,
    }


def _company():
    return {
        "name": "Aperture",
        "stage": "seed",
        "ask": 1_500_000,
        "sectors": ["dual-use", "sensors"],
        "geography": ["us"],
        "keywords": ["prototype"],
        "dilution_pref": "non-dilutive",
        "dual_use": "dual-use",
        "trl": 4,
    }


def test_perfect_match_scores_100():
    m = score_match(_company(), _perfect_source())
    assert m.score == pytest.approx(100.0)
    assert m.band == "strong"


def test_every_factor_has_a_reason():
    m = score_match(_company(), _perfect_source())
    assert len(m.factors) == len(DEFAULT_FACTORS)
    assert all(isinstance(f, FactorScore) and f.reason for f in m.factors)


def test_score_reconciles_to_weighted_factors():
    m = score_match(_company(), _perfect_source())
    live = [f for f in m.factors if not f.abstained]
    manual = 100.0 * sum(f.weight * f.raw for f in live) / sum(f.weight for f in live)
    assert m.score == pytest.approx(manual)


def test_missing_fields_cause_abstention_not_crash():
    m = score_match({"name": "sparse"}, {"name": "src"})
    assert all(f.abstained for f in m.factors)
    assert m.score == 0.0  # nothing to score
    assert m.effective_weight == 0.0


def test_abstaining_factors_excluded_from_denominator():
    # company only supplies stage; only the stage factor should count
    company = {"name": "c", "stage": "seed"}
    source = {"name": "s", "stages": ["seed"]}
    m = score_match(company, source)
    live = [f for f in m.factors if not f.abstained]
    assert [f.name for f in live] == ["stage"]
    assert m.score == pytest.approx(100.0)


def test_check_size_below_band_scores_partial():
    company = {"name": "c", "ask": 100_000}
    source = {"name": "s", "check_min": 1_000_000, "check_max": 2_000_000}
    m = score_match(company, source)
    cs = next(f for f in m.factors if f.name == "check_size")
    assert 0.0 < cs.raw < 1.0
    assert "below" in cs.reason


def test_non_dilutive_seeker_penalized_for_equity_source():
    company = {"name": "c", "dilution_pref": "non-dilutive"}
    source = {"name": "s", "dilution": ["equity"]}
    m = score_match(company, source)
    d = next(f for f in m.factors if f.name == "dilution")
    assert d.raw is not None and d.raw < 0.3


def test_stage_adjacency_partial_credit():
    company = {"name": "c", "stage": "seed"}
    source = {"name": "s", "stages": ["series-a"]}  # one step away
    m = score_match(company, source)
    st = next(f for f in m.factors if f.name == "stage")
    assert 0.5 < st.raw < 1.0


def test_weights_override_changes_score():
    company = _company()
    source = _perfect_source()
    # zero out sector weight -> still 100 since all perfect, so instead break sector
    source["thesis"] = ["unrelated"]
    base = score_match(company, source).score
    heavy = score_match(company, source, weights={"sector": 10.0}).score
    assert heavy < base  # heavily weighting the poor factor lowers the score


def test_bad_profile_type_raises():
    with pytest.raises(DealflowError):
        score_match("not a dict", {})


def test_factor_error_abstains_gracefully():
    def boom(_c, _s):
        raise RuntimeError("kaboom")
    m = score_match({"name": "c"}, {"name": "s"}, factors={"boom": (1.0, boom)})
    f = m.factors[0]
    assert f.abstained and "abstained" in f.reason


# --------------------------------------------------------------------------- #
# ranking
# --------------------------------------------------------------------------- #
def test_rank_matches_sorted_desc():
    company = _company()
    sources = [
        {"name": "bad", "stages": ["public"], "thesis": ["unrelated"]},
        _perfect_source(),
    ]
    ranked = rank_matches(company, sources)
    assert ranked[0].source == "Perfect Fit Fund"
    assert ranked[0].score >= ranked[1].score


def test_rank_top_and_min_score_filters():
    company = _company()
    sources = [_perfect_source(), {"name": "bad", "stages": ["public"], "thesis": ["nope"]}]
    assert len(rank_matches(company, sources, top=1)) == 1
    assert all(m.score >= 90 for m in rank_matches(company, sources, min_score=90))


def test_rank_requires_list():
    with pytest.raises(DealflowError):
        rank_matches(_company(), {"not": "a list"})


# --------------------------------------------------------------------------- #
# result helpers
# --------------------------------------------------------------------------- #
def test_bands():
    def band(s):
        return MatchResult("c", "s", s, [], 1.0).band
    assert band(85) == "strong"
    assert band(65) == "promising"
    assert band(45) == "possible"
    assert band(10) == "weak"


def test_top_factors_and_gaps():
    company = _company()
    source = _perfect_source()
    source["thesis"] = ["unrelated"]  # make sector a gap
    m = score_match(company, source)
    assert any(f.name == "sector" for f in m.gaps())
    assert len(m.top_factors(2)) <= 2


def test_to_dict_roundtrips_fields():
    m = score_match(_company(), _perfect_source())
    d = m.to_dict()
    assert d["company"] == "Aperture"
    assert d["band"] == "strong"
    assert len(d["factors"]) == len(DEFAULT_FACTORS)
    assert all("reason" in f for f in d["factors"])


def test_explain_is_human_readable():
    m = score_match(_company(), _perfect_source())
    text = explain(m)
    assert "Aperture" in text
    assert "fit:" in text
    for f in m.factors:
        assert f.name in text
