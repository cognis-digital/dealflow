"""Edge-case tests for DEALFLOW's built-in YAML subset parser.

The parser is deliberately small but must be predictable: block maps, block
lists, lists-of-mappings, inline flow mappings, comments, quotes, scalar
coercion, and clear errors on the things it does NOT support (tabs, etc.).
"""
import pytest

from dealflow.core import DealflowError, _coerce, _parse_flow_mapping, _yaml_load


# --------------------------------------------------------------------------- #
# scalar coercion
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw,expected", [
    ("true", True), ("True", True), ("yes", True), ("YES", True),
    ("false", False), ("no", False), ("No", False),
    ("null", None), ("~", None), ("none", None), ("None", None),
    ("42", 42), ("-7", -7), ("0", 0),
    ("3.5", 3.5), ("-0.25", -0.25),
    ("hello", "hello"),
    ("", None),
])
def test_coerce_scalars(raw, expected):
    assert _coerce(raw) == expected


def test_coerce_strips_matching_quotes():
    assert _coerce('"quoted"') == "quoted"
    assert _coerce("'quoted'") == "quoted"


def test_coerce_keeps_number_like_string_when_quoted():
    assert _coerce('"42"') == "42"
    assert _coerce("'true'") == "true"


def test_coerce_preserves_internal_whitespace():
    assert _coerce("  hello world  ") == "hello world"


# --------------------------------------------------------------------------- #
# flow mappings
# --------------------------------------------------------------------------- #
def test_flow_mapping_basic():
    assert _parse_flow_mapping("{name: lost, type: lost}") == {
        "name": "lost", "type": "lost"
    }


def test_flow_mapping_empty():
    assert _parse_flow_mapping("{}") == {}


def test_flow_mapping_coerces_values():
    out = _parse_flow_mapping("{terminal: true, order: 3}")
    assert out == {"terminal": True, "order": 3}


def test_flow_mapping_strips_quotes_on_keys_and_values():
    out = _parse_flow_mapping('{"name": "won"}')
    assert out == {"name": "won"}


def test_flow_mapping_missing_colon_raises():
    with pytest.raises(DealflowError):
        _parse_flow_mapping("{namewon}")


def test_flow_mapping_empty_key_raises():
    with pytest.raises(DealflowError):
        _parse_flow_mapping("{: value}")


def test_coerce_dispatches_to_flow_mapping():
    assert _coerce("{name: x, type: y}") == {"name": "x", "type": "y"}


# --------------------------------------------------------------------------- #
# block structures
# --------------------------------------------------------------------------- #
def test_simple_map():
    assert _yaml_load("a: 1\nb: two\n") == {"a": 1, "b": "two"}


def test_block_list_of_scalars():
    assert _yaml_load("- a\n- b\n- c\n") == ["a", "b", "c"]


def test_nested_map():
    data = _yaml_load("name: p\nmeta:\n  owner: x\n  count: 3\n")
    assert data == {"name": "p", "meta": {"owner": "x", "count": 3}}


def test_list_of_block_mappings():
    text = "stages:\n  - name: a\n    type: open\n  - name: b\n    type: won\n"
    data = _yaml_load(text)
    assert data["stages"][0] == {"name": "a", "type": "open"}
    assert data["stages"][1] == {"name": "b", "type": "won"}


def test_list_of_flow_mappings():
    text = "stages:\n  - {name: a, type: open}\n  - {name: b, type: won}\n"
    data = _yaml_load(text)
    assert data["stages"] == [
        {"name": "a", "type": "open"},
        {"name": "b", "type": "won"},
    ]


def test_comments_and_blank_lines_ignored():
    text = "# header\n\nname: p   # trailing comment\n\nstages:\n  - a  # inline\n"
    data = _yaml_load(text)
    assert data == {"name": "p", "stages": ["a"]}


def test_hash_inside_quotes_is_not_a_comment():
    data = _yaml_load('name: "a # b"\n')
    assert data == {"name": "a # b"}


def test_empty_document_is_empty_mapping():
    assert _yaml_load("") == {}
    assert _yaml_load("\n\n# only a comment\n") == {}


def test_tabs_in_indentation_raise():
    with pytest.raises(DealflowError):
        _yaml_load("name: p\n\tbad: 1\n")


def test_map_line_without_colon_raises():
    with pytest.raises(DealflowError):
        _yaml_load("name p\n")
