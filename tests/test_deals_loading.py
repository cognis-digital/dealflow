"""Tests for the CSV deal-log loader: parsing, normalization, error paths."""
import datetime as dt
import os

import pytest

from dealflow.core import DealflowError, Deal, load_deals, _parse_date


def L(text):
    return load_deals(text, is_text=True)


# --------------------------------------------------------------------------- #
# date parsing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("s,expected", [
    ("2026-01-15", dt.date(2026, 1, 15)),
    ("2026/01/15", dt.date(2026, 1, 15)),
    ("01/15/2026", dt.date(2026, 1, 15)),
    ("01-15-2026", dt.date(2026, 1, 15)),
    ("  2026-01-15  ", dt.date(2026, 1, 15)),
])
def test_parse_date_formats(s, expected):
    assert _parse_date(s) == expected


def test_parse_date_empty_raises():
    with pytest.raises(DealflowError, match="empty date"):
        _parse_date("")


def test_parse_date_garbage_raises():
    with pytest.raises(DealflowError, match="unrecognized date"):
        _parse_date("last tuesday")


# --------------------------------------------------------------------------- #
# happy-path loading
# --------------------------------------------------------------------------- #
def test_basic_load_and_history_sorted():
    deals = L(
        "deal_id,stage,date,amount\n"
        "A,lead,2026-01-10,100\n"
        "A,qualified,2026-01-01,100\n"  # out of order on purpose
    )
    assert len(deals) == 1
    d = deals[0]
    dates = [dd for _, dd in d.history]
    assert dates == sorted(dates)  # loader sorts chronologically


def test_amount_takes_max_seen():
    deals = L(
        "deal_id,stage,date,amount\n"
        "A,lead,2026-01-01,100\n"
        "A,qualified,2026-01-08,250\n"
        "A,proposal,2026-01-15,180\n"
    )
    assert deals[0].amount == 250.0


def test_currency_symbols_and_commas_normalized():
    deals = L('deal_id,stage,date,amount\nA,lead,2026-01-01,"$1,250,000"\n')
    assert deals[0].amount == 1_250_000.0


def test_missing_amount_column_yields_zero_value():
    deals = L("deal_id,stage,date\nA,lead,2026-01-01\n")
    assert deals[0].amount == 0.0


def test_blank_amount_cell_is_zero():
    deals = L("deal_id,stage,date,amount\nA,lead,2026-01-01,\n")
    assert deals[0].amount == 0.0


def test_case_insensitive_headers():
    deals = L("Deal_ID,STAGE,Date,Amount\nA,lead,2026-01-01,100\n")
    assert deals[0].deal_id == "A" and deals[0].amount == 100.0


def test_headers_with_surrounding_spaces():
    deals = L(" deal_id , stage , date , amount \nA,lead,2026-01-01,100\n")
    assert deals[0].deal_id == "A"


def test_blank_deal_id_rows_skipped():
    deals = L(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\n"
        ",qualified,2026-01-08\n"  # skipped
    )
    assert [d.deal_id for d in deals] == ["A"]


def test_deals_sorted_by_id():
    deals = L(
        "deal_id,stage,date\n"
        "Z,lead,2026-01-01\n"
        "A,lead,2026-01-01\n"
        "M,lead,2026-01-01\n"
    )
    assert [d.deal_id for d in deals] == ["A", "M", "Z"]


def test_current_stage_is_last_by_date():
    deals = L(
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\n"
        "A,won,2026-02-01\n"
    )
    assert deals[0].current_stage == "won"


# --------------------------------------------------------------------------- #
# error paths
# --------------------------------------------------------------------------- #
def test_empty_csv_raises():
    with pytest.raises(DealflowError, match="empty"):
        L("")


def test_missing_required_column_raises():
    with pytest.raises(DealflowError, match="missing required column"):
        L("deal_id,stage\nA,lead\n")


def test_empty_stage_cell_raises_with_row_number():
    with pytest.raises(DealflowError, match="row 2"):
        L("deal_id,stage,date\nA,,2026-01-01\n")


def test_bad_date_reports_row_and_deal():
    with pytest.raises(DealflowError, match="row 2.*A"):
        L("deal_id,stage,date\nA,lead,nope\n")


def test_non_numeric_amount_raises():
    with pytest.raises(DealflowError, match="not a number"):
        L("deal_id,stage,date,amount\nA,lead,2026-01-01,lots\n")


def test_negative_amount_raises():
    with pytest.raises(DealflowError, match="negative"):
        L("deal_id,stage,date,amount\nA,lead,2026-01-01,-5\n")


def test_row_number_accounts_for_header():
    # third data row (line 4) is the offender
    text = (
        "deal_id,stage,date\n"
        "A,lead,2026-01-01\n"
        "B,lead,2026-01-02\n"
        "C,lead,bad-date\n"
    )
    with pytest.raises(DealflowError, match="row 4"):
        L(text)


# --------------------------------------------------------------------------- #
# file-based loading
# --------------------------------------------------------------------------- #
def test_load_from_file(tmp_path):
    p = tmp_path / "deals.csv"
    p.write_text("deal_id,stage,date,amount\nA,lead,2026-01-01,100\n", encoding="utf-8")
    deals = load_deals(str(p))
    assert deals[0].amount == 100.0


def test_missing_file_raises_oserror():
    with pytest.raises(OSError):
        load_deals(os.path.join("definitely", "not", "here.csv"))


def test_deal_dataclass_current_stage():
    d = Deal(deal_id="X", amount=1.0, history=[("a", dt.date(2026, 1, 1)),
                                               ("b", dt.date(2026, 1, 2))])
    assert d.current_stage == "b"
