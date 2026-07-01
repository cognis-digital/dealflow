"""Tests for pipeline parsing, validation, and the state-machine model."""
import pytest

from dealflow.core import DealflowError, Pipeline, Stage, parse_pipeline


def test_string_shorthand_stages():
    p = parse_pipeline("name: P\nstages:\n  - a\n  - b\n  - c\n")
    assert [s.name for s in p.stages] == ["a", "b", "c"]
    # last non-terminal stage becomes the won stage by default
    assert p.won_stage == "c"
    assert p.stage("c").won and p.stage("c").terminal


def test_default_name_when_missing():
    p = parse_pipeline("stages:\n  - a\n  - b\n")
    assert p.name == "pipeline"


def test_explicit_won_and_lost_types():
    p = parse_pipeline(
        "name: P\nstages:\n  - lead\n  - name: won\n    type: won\n"
        "  - name: lost\n    type: lost\n"
    )
    assert p.won_stage == "won"
    assert p.lost_stages == {"lost"}
    assert p.stage("won").won
    assert p.stage("lost").terminal and not p.stage("lost").won


def test_terminal_synonyms_are_terminal_but_not_won():
    for kind in ("lost", "closed", "terminal"):
        p = parse_pipeline(
            f"name: P\nstages:\n  - a\n  - name: b\n    type: {kind}\n"
        )
        # 'b' is terminal-loss; 'a' is promoted to won
        assert p.won_stage == "a"
        assert "b" in p.lost_stages


def test_won_via_boolean_flag():
    p = parse_pipeline("name: P\nstages:\n  - a\n  - name: w\n    won: true\n")
    assert p.won_stage == "w"


def test_terminal_via_boolean_flag():
    p = parse_pipeline(
        "name: P\nstages:\n  - a\n  - name: w\n    won: true\n"
        "  - name: dead\n    terminal: true\n"
    )
    assert "dead" in p.lost_stages


# --------------------------------------------------------------------------- #
# validation / error paths
# --------------------------------------------------------------------------- #
def test_top_level_must_be_mapping():
    with pytest.raises(DealflowError, match="mapping at the top level"):
        parse_pipeline("- a\n- b\n")


def test_missing_stages_raises():
    with pytest.raises(DealflowError, match="non-empty 'stages'"):
        parse_pipeline("name: P\n")


def test_empty_stages_list_raises():
    with pytest.raises(DealflowError, match="non-empty 'stages'"):
        parse_pipeline("name: P\nstages:\n")


def test_stage_missing_name_raises():
    with pytest.raises(DealflowError, match="missing 'name'"):
        parse_pipeline("name: P\nstages:\n  - type: open\n")


def test_duplicate_stage_name_raises():
    with pytest.raises(DealflowError, match="duplicate stage name"):
        parse_pipeline("name: P\nstages:\n  - a\n  - a\n")


def test_more_than_one_won_stage_raises():
    with pytest.raises(DealflowError, match="more than one 'won'"):
        parse_pipeline(
            "name: P\nstages:\n  - {name: a, type: won}\n  - {name: b, type: won}\n"
        )


def test_won_fallback_never_lands_on_a_lost_stage():
    # No explicit won stage; last stage is lost. The fallback must promote the
    # last NON-terminal stage (a), not the lost stage (this was a real bug).
    p = parse_pipeline(
        "name: P\nstages:\n  - a\n  - qualified\n  - name: lost\n    type: lost\n"
    )
    assert p.won_stage == "qualified"
    assert p.won_stage not in p.lost_stages


def test_all_terminal_stages_raises():
    with pytest.raises(DealflowError, match="no open stages"):
        parse_pipeline(
            "name: P\nstages:\n  - {name: a, type: lost}\n  - {name: b, type: lost}\n"
        )


def test_stage_must_be_string_or_mapping():
    with pytest.raises(DealflowError, match="string or mapping"):
        parse_pipeline("name: P\nstages:\n  - 5\n  -\n    - nested\n")


# --------------------------------------------------------------------------- #
# Pipeline object behavior
# --------------------------------------------------------------------------- #
def _pipe():
    return parse_pipeline(
        "name: P\nstages:\n  - lead\n  - qualified\n  - name: won\n    type: won\n"
        "  - name: lost\n    type: lost\n"
    )


def test_pipeline_stage_lookup_and_index():
    p = _pipe()
    assert p.stage("qualified").order == 1
    assert p.index("won") == 2


def test_pipeline_unknown_stage_lookup_raises():
    with pytest.raises(DealflowError, match="unknown stage"):
        _pipe().stage("nope")


def test_open_stages_excludes_terminal():
    p = _pipe()
    assert [s.name for s in p.open_stages] == ["lead", "qualified"]


def test_stage_dataclass_defaults():
    s = Stage(name="x", order=0)
    assert s.terminal is False and s.won is False


def test_pipeline_dataclass_construction():
    p = Pipeline(name="P", stages=[Stage("a", 0)], won_stage="a")
    assert p.lost_stages == set()
