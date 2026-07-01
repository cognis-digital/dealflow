"""Tests for the analysis engine: conversion, velocity, forecast, risk-adjust.

These lock in the math (advance rates, P(win), weighted forecast, velocity) and
guard the state-machine transition rules — including the regression where a move
INTO a lost stage was wrongly counted as an advance.
"""
import pytest

from dealflow.core import DealflowError, analyze, load_deals, parse_pipeline

PIPE = (
    "name: P\nstages:\n  - lead\n  - qualified\n  - proposal\n"
    "  - name: won\n    type: won\n  - name: lost\n    type: lost\n"
)


def run(csv_text, pipe_text=PIPE):
    p = parse_pipeline(pipe_text)
    d = load_deals(csv_text, is_text=True)
    return p, d, analyze(p, d)


def by(rep):
    return {s["stage"]: s for s in rep.stages}


# --------------------------------------------------------------------------- #
# counts & classification
# --------------------------------------------------------------------------- #
def test_empty_deal_list_is_all_zero():
    p = parse_pipeline(PIPE)
    rep = analyze(p, [])
    assert rep.total_deals == 0
    assert rep.open_deals == rep.won_deals == rep.lost_deals == 0
    assert rep.weighted_forecast == 0.0
    assert rep.overall_win_rate == 0.0


def test_win_rate_only_counts_decided_deals():
    # 1 won, 1 lost, 1 still open -> win rate = 1/2, not 1/3
    rep = run(
        "deal_id,stage,date\n"
        "W,lead,2026-01-01\nW,won,2026-02-01\n"
        "L,lead,2026-01-01\nL,lost,2026-02-01\n"
        "O,lead,2026-01-01\n"
    )[2]
    assert rep.won_deals == 1 and rep.lost_deals == 1 and rep.open_deals == 1
    assert rep.overall_win_rate == 0.5


def test_all_open_gives_zero_win_rate_not_crash():
    rep = run("deal_id,stage,date\nA,lead,2026-01-01\nB,qualified,2026-01-02\n")[2]
    assert rep.overall_win_rate == 0.0
    assert rep.open_deals == 2


def test_won_and_open_value_split():
    rep = run(
        "deal_id,stage,date,amount\n"
        "W,lead,2026-01-01,1000\nW,won,2026-02-01,1000\n"
        "O,lead,2026-01-01,500\n"
    )[2]
    assert rep.won_value == 1000.0
    assert rep.open_value == 500.0


def test_lost_deals_excluded_from_open_value():
    rep = run(
        "deal_id,stage,date,amount\n"
        "L,lead,2026-01-01,999\nL,lost,2026-02-01,999\n"
    )[2]
    assert rep.open_value == 0.0
    assert rep.lost_deals == 1


# --------------------------------------------------------------------------- #
# advance rates & the lost-advance regression
# --------------------------------------------------------------------------- #
def test_advance_rate_is_advanced_over_entered():
    # 4 enter lead, 3 advance to qualified
    rep = run(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\nA,qualified,2026-01-08\n"
        "B,lead,2026-01-01\nB,qualified,2026-01-08\n"
        "C,lead,2026-01-01\nC,qualified,2026-01-08\n"
        "D,lead,2026-01-01\n"
    )[2]
    b = by(rep)
    assert b["lead"]["entered"] == 4
    assert b["lead"]["advanced"] == 3
    assert b["lead"]["advance_rate"] == round(3 / 4, 4)


def test_move_into_lost_is_not_an_advance():
    # Regression: lead -> lost must NOT count as advancing out of lead.
    rep = run(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\nA,lost,2026-01-15\n"
    )[2]
    b = by(rep)
    assert b["lead"]["entered"] == 1
    assert b["lead"]["advanced"] == 0
    assert b["lead"]["advance_rate"] == 0.0


def test_zero_win_history_forecasts_zero():
    # Every deal lost; one still open. P(win) must be 0 -> forecast 0.
    rep = run(
        "deal_id,stage,date,amount\n"
        "A,lead,2026-01-01,100\nA,lost,2026-01-15,100\n"
        "B,lead,2026-01-01,100\nB,lost,2026-01-15,100\n"
        "C,lead,2026-01-01,100\n"  # open, but no deal ever won
    )[2]
    assert rep.weighted_forecast == 0.0
    assert by(rep)["lead"]["p_win"] == 0.0


def test_terminal_stages_have_no_advance_rate():
    rep = run("deal_id,stage,date\nA,lead,2026-01-01\nA,won,2026-02-01\n")[2]
    b = by(rep)
    assert b["won"]["advance_rate"] is None
    assert b["lost"]["advance_rate"] is None


# --------------------------------------------------------------------------- #
# P(win) chain
# --------------------------------------------------------------------------- #
def test_p_win_is_product_of_downstream_advance_rates():
    # lead->qualified 100%, qualified->proposal 50%, proposal->won 100%.
    rep = run(
        "deal_id,stage,date\n"
        # two deals reach proposal, one of them wins
        "A,lead,2026-01-01\nA,qualified,2026-01-08\nA,proposal,2026-01-15\nA,won,2026-01-22\n"
        "B,lead,2026-01-01\nB,qualified,2026-01-08\nB,proposal,2026-01-15\n"
        # two deals reach qualified, only these two advanced there in total...
        "C,lead,2026-01-01\nC,qualified,2026-01-08\n"
        "D,lead,2026-01-01\nD,qualified,2026-01-08\n"
    )[2]
    b = by(rep)
    # lead->qualified: 4/4 = 1.0 ; qualified->proposal: 2/4 = 0.5 ; proposal->won: 1/2 = 0.5
    assert b["lead"]["advance_rate"] == 1.0
    assert b["qualified"]["advance_rate"] == 0.5
    assert b["proposal"]["advance_rate"] == 0.5
    # P(win|lead) = 1.0 * 0.5 * 0.5 = 0.25
    assert b["lead"]["p_win"] == 0.25
    assert b["qualified"]["p_win"] == 0.25
    assert b["proposal"]["p_win"] == 0.5


def test_p_win_monotonic_non_decreasing_along_open_stages():
    rep = run(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\nA,qualified,2026-01-08\nA,proposal,2026-01-15\nA,won,2026-01-22\n"
        "B,lead,2026-01-01\nB,qualified,2026-01-08\n"
        "C,lead,2026-01-01\n"
    )[2]
    b = by(rep)
    assert b["lead"]["p_win"] <= b["qualified"]["p_win"] <= b["proposal"]["p_win"]
    assert b["won"]["p_win"] == 1.0
    assert b["lost"]["p_win"] == 0.0


# --------------------------------------------------------------------------- #
# weighted forecast / expected value
# --------------------------------------------------------------------------- #
def test_expected_value_equals_amount_times_pwin_for_open():
    rep = run(
        "deal_id,stage,date,amount\n"
        "A,lead,2026-01-01,1000\nA,qualified,2026-01-08,1000\nA,proposal,2026-01-15,1000\nA,won,2026-01-22,1000\n"
        "B,lead,2026-01-01,1000\nB,qualified,2026-01-08,1000\nB,proposal,2026-01-15,1000\n"
    )[2]
    b = by(rep)
    open_row = next(d for d in rep.deals if d["status"] == "open")
    expected = round(open_row["amount"] * b[open_row["current_stage"]]["p_win"], 2)
    assert open_row["expected_value"] == expected


def test_won_and_lost_rows_contribute_zero_expected_value():
    rep = run(
        "deal_id,stage,date,amount\n"
        "W,lead,2026-01-01,500\nW,won,2026-02-01,500\n"
        "L,lead,2026-01-01,500\nL,lost,2026-02-01,500\n"
    )[2]
    for d in rep.deals:
        if d["status"] in ("won", "lost"):
            assert d["expected_value"] == 0.0


def test_weighted_forecast_never_exceeds_open_value():
    rep = run(
        "deal_id,stage,date,amount\n"
        "A,lead,2026-01-01,1000\nA,qualified,2026-01-08,1000\n"
        "B,lead,2026-01-01,2000\n"
    )[2]
    assert rep.weighted_forecast <= rep.open_value


def test_forecast_reconciles_to_sum_of_open_expected_values():
    rep = run(
        "deal_id,stage,date,amount\n"
        "A,lead,2026-01-01,1000\nA,qualified,2026-01-08,1000\nA,proposal,2026-01-15,1000\nA,won,2026-01-22,1000\n"
        "B,lead,2026-01-01,3000\nB,qualified,2026-01-08,3000\n"
        "C,lead,2026-01-01,2000\n"
    )[2]
    ev = sum(d["expected_value"] for d in rep.deals if d["status"] == "open")
    assert abs(ev - rep.weighted_forecast) < 0.05


# --------------------------------------------------------------------------- #
# velocity
# --------------------------------------------------------------------------- #
def test_velocity_is_average_days_in_stage():
    rep = run(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\nA,qualified,2026-01-11\n"   # 10 days in lead
        "B,lead,2026-01-01\nB,qualified,2026-01-21\n"   # 20 days in lead
    )[2]
    assert by(rep)["lead"]["avg_days_in_stage"] == 15.0


def test_velocity_none_when_no_deal_left_stage():
    rep = run("deal_id,stage,date\nA,lead,2026-01-01\n")[2]
    # nobody left 'lead' (single event) -> no duration recorded
    assert by(rep)["lead"]["avg_days_in_stage"] is None


def test_age_days_is_first_to_last_event():
    rep = run(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\nA,qualified,2026-01-31\n"
    )[2]
    row = next(d for d in rep.deals if d["deal_id"] == "A")
    assert row["age_days"] == 30


def test_single_event_deal_has_zero_age():
    rep = run("deal_id,stage,date\nA,lead,2026-01-01\n")[2]
    assert rep.deals[0]["age_days"] == 0


# --------------------------------------------------------------------------- #
# unknown stage guard & to_dict
# --------------------------------------------------------------------------- #
def test_deal_with_unknown_stage_raises():
    p = parse_pipeline(PIPE)
    d = load_deals("deal_id,stage,date\nA,ghost,2026-01-01\n", is_text=True)
    with pytest.raises(DealflowError, match="unknown stage"):
        analyze(p, d)


def test_report_to_dict_rounds_and_has_all_keys():
    rep = run("deal_id,stage,date,amount\nA,lead,2026-01-01,1000\n")[2]
    doc = rep.to_dict()
    assert set(doc) >= {
        "pipeline", "total_deals", "open_deals", "won_deals", "lost_deals",
        "open_value", "won_value", "weighted_forecast", "overall_win_rate",
        "stages", "deals",
    }
    assert doc["total_deals"] == 1


def test_deal_visited_stage_once_counted_once():
    # A deal that revisits a stage should only be counted as entering it once.
    rep = run(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\nA,qualified,2026-01-08\nA,lead,2026-01-15\n"
    )[2]
    assert by(rep)["lead"]["entered"] == 1


def test_single_stage_pipeline_all_won():
    rep = run(
        "deal_id,stage,date,amount\nA,closed,2026-01-01,100\nB,closed,2026-01-02,200\n",
        pipe_text="name: One\nstages:\n  - closed\n",
    )[2]
    assert rep.won_deals == 2
    assert rep.open_deals == 0
    assert rep.weighted_forecast == 0.0
