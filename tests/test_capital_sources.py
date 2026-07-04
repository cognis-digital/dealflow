"""Tests for the capital-source taxonomy (dealflow.capital_sources)."""
import json

import pytest

from dealflow.core import DealflowError
from dealflow.capital_sources import (
    SEED_SOURCES,
    SourceCatalog,
    default_catalog,
    load_catalog,
    merged_catalog,
    parse_catalog,
)


def test_seed_catalog_nonempty_and_well_formed():
    cat = default_catalog()
    assert len(cat.sources) == len(SEED_SOURCES) >= 10
    for s in cat.sources:
        assert s["id"]
        assert s["category"]
        assert isinstance(s["check_min"], int)
        assert s["check_max"] >= s["check_min"]
        assert s["dilution"]


def test_default_catalog_returns_fresh_copies():
    a = default_catalog()
    a.sources[0]["name"] = "MUTATED"
    b = default_catalog()
    assert b.sources[0]["name"] != "MUTATED"


def test_ids_and_get():
    cat = default_catalog()
    assert "sbir-phase-i" in cat.ids()
    assert cat.get("sbir-phase-i")["category"] == "non-dilutive-grant"
    assert cat.get("SBIR-Phase-I")["id"] == "sbir-phase-i"  # case-insensitive


def test_get_unknown_raises():
    with pytest.raises(DealflowError):
        default_catalog().get("no-such-source")


def test_by_category_and_categories():
    cat = default_catalog()
    cats = cat.categories()
    assert "equity-vc" in cats
    vc = cat.by_category("equity-vc")
    assert vc and all(s["category"] == "equity-vc" for s in vc)


def test_duplicate_id_rejected():
    with pytest.raises(DealflowError):
        SourceCatalog(sources=[{"id": "x"}, {"id": "x"}])


def test_source_missing_id_rejected():
    with pytest.raises(DealflowError):
        SourceCatalog(sources=[{"category": "vc"}])


def test_catalog_must_be_list():
    with pytest.raises(DealflowError):
        SourceCatalog(sources={"not": "a list"})


def test_merge_overrides_by_id():
    cat = default_catalog()
    merged = cat.merge([{"id": "sbir-phase-i", "name": "OVERRIDDEN", "category": "custom"}])
    assert merged.get("sbir-phase-i")["name"] == "OVERRIDDEN"
    # non-overridden entries preserved
    assert merged.get("defense-vc")["name"] == "Defense-focused venture capital"


def test_merge_adds_new_entries():
    cat = default_catalog()
    n = len(cat.sources)
    merged = cat.merge([{"id": "my-fund", "name": "My Fund", "category": "equity-vc"}])
    assert len(merged.sources) == n + 1
    assert merged.get("my-fund")["name"] == "My Fund"


def test_parse_catalog_yaml_list():
    text = """
- id: a
  name: A
  category: equity-vc
- id: b
  name: B
  category: grant
"""
    cat = parse_catalog(text)
    assert cat.ids() == ["a", "b"]


def test_parse_catalog_json_and_wrapped():
    j = json.dumps({"sources": [{"id": "a", "name": "A", "category": "vc"}]})
    cat = parse_catalog(j)
    assert cat.ids() == ["a"]


def test_load_and_merged_catalog_from_file(tmp_path):
    p = tmp_path / "cat.yml"
    p.write_text("- id: my-fund\n  name: My Fund\n  category: equity-vc\n", encoding="utf-8")
    assert load_catalog(str(p)).ids() == ["my-fund"]
    merged = merged_catalog(str(p))
    assert "my-fund" in merged.ids()
    assert "sbir-phase-i" in merged.ids()  # seed still present


def test_merged_catalog_no_user_path_is_seed():
    assert merged_catalog(None).ids() == default_catalog().ids()


def test_to_dict():
    d = default_catalog().to_dict()
    assert d["count"] == len(SEED_SOURCES)
    assert isinstance(d["sources"], list)
