"""Tests for the opportunity/capture pipeline tracker (dealflow.opps)."""
import datetime as dt

import pytest

from dealflow.core import DealflowError
from dealflow.opps import (
    DEFAULT_STAGES,
    Opp,
    PipelineTracker,
    parse_tracker,
)


def _tracker(**kw):
    opps = [
        Opp.from_dict({"id": "o1", "name": "A", "stage": "proposal", "value": 100000}),
        Opp.from_dict({"id": "o2", "name": "B", "stage": "submitted", "value": 50000}),
        Opp.from_dict({"id": "o3", "name": "C", "stage": "awarded", "value": 30000}),
        Opp.from_dict({"id": "o4", "name": "D", "stage": "lost", "value": 20000}),
    ]
    return PipelineTracker(opps=opps, **kw)


def test_opp_from_dict_coerces_value():
    o = Opp.from_dict({"id": "x", "value": "$1,200,000"})
    assert o.value == 1_200_000


def test_opp_requires_id_or_name():
    with pytest.raises(DealflowError):
        Opp.from_dict({"value": 1})


def test_opp_rejects_negative_value():
    with pytest.raises(DealflowError):
        Opp.from_dict({"id": "x", "value": -5})


def test_opp_rejects_out_of_range_probability():
    with pytest.raises(DealflowError):
        Opp.from_dict({"id": "x", "probability": 1.5})


def test_default_stage_probability_used():
    t = _tracker()
    o = next(o for o in t.opps if o.id == "o1")
    # proposal baseline is 0.5 in DEFAULT_STAGES
    assert t.probability(o) == 0.5
    assert t.weighted_value(o) == 50000


def test_explicit_probability_overrides_stage():
    o = Opp.from_dict({"id": "x", "stage": "proposal", "value": 100, "probability": 0.9})
    t = PipelineTracker(opps=[o])
    assert t.probability(o) == 0.9


def test_open_won_lost_classification():
    t = _tracker()
    s = t.summary()
    assert s["open"] == 2       # proposal + submitted
    assert s["won"] == 1        # awarded (p=1.0)
    assert s["lost"] == 1       # lost (p=0.0)


def test_weighted_pipeline_only_counts_open():
    t = _tracker()
    s = t.summary()
    # 100000*0.5 + 50000*0.65
    assert s["weighted_pipeline"] == pytest.approx(100000 * 0.5 + 50000 * 0.65)


def test_summary_sorted_by_weighted_value_desc():
    t = _tracker()
    rows = t.summary()["opportunities"]
    wv = [r["weighted_value"] for r in rows]
    assert wv == sorted(wv, reverse=True)


def test_next_action_present_for_open():
    t = _tracker()
    o = next(o for o in t.opps if o.id == "o1")
    assert t.next_action(o)  # non-empty from the playbook


def test_stale_flag_and_action():
    o = Opp.from_dict({"id": "x", "stage": "proposal", "value": 100, "updated": "2026-01-01"})
    t = PipelineTracker(opps=[o], stale_days=30)
    today = dt.date(2026, 6, 1)
    assert t.is_stale(o, today=today)
    assert t.next_action(o, today=today).startswith("STALE")


def test_won_opp_never_stale():
    o = Opp.from_dict({"id": "x", "stage": "awarded", "value": 100, "updated": "2020-01-01"})
    t = PipelineTracker(opps=[o])
    assert not t.is_stale(o, today=dt.date(2026, 6, 1))


def test_duplicate_opp_id_rejected():
    with pytest.raises(DealflowError):
        PipelineTracker(opps=[Opp.from_dict({"id": "a"}), Opp.from_dict({"id": "a"})])


def test_unknown_stage_raises():
    o = Opp.from_dict({"id": "x", "stage": "nonsense", "value": 1})
    t = PipelineTracker(opps=[o])
    with pytest.raises(DealflowError):
        t.summary()


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
def test_parse_tracker_yaml_mapping():
    text = """
stale_days: 15
opportunities:
  - id: o1
    name: One
    stage: capture
    value: 5000
"""
    t = parse_tracker(text)
    assert t.stale_days == 15
    assert len(t.opps) == 1
    assert t.opps[0].stage == "capture"


def test_parse_tracker_bare_list():
    text = "- id: o1\n  stage: proposal\n  value: 10\n"
    t = parse_tracker(text)
    assert t.opps[0].id == "o1"


def test_parse_tracker_custom_stages():
    text = """
stages:
  - name: intro
    probability: 0.1
    action: reach out
  - name: closed
    probability: 1.0
opportunities:
  - id: o1
    stage: intro
    value: 100
"""
    t = parse_tracker(text)
    o = t.opps[0]
    assert t.probability(o) == 0.1
    assert t.next_action(o) == "reach out"


def test_parse_tracker_bad_top_type():
    with pytest.raises(DealflowError):
        parse_tracker("just a string")


def test_default_stages_have_actions():
    assert all(s.get("action") is not None for s in DEFAULT_STAGES)
    names = {s["name"] for s in DEFAULT_STAGES}
    assert {"identified", "proposal", "awarded", "lost"} <= names
