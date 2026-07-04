"""Capital-source taxonomy — a structured, extensible catalog of funding vehicles.

This is the *knowledge base* the matchmaking engine scores against. Each entry
describes a **category** of funding vehicle at the level of publicly documented,
unclassified program design: what it funds, typical size, whether it dilutes
equity, its rough timeline, and heuristics for when it fits. No private-party
PII, no non-public program data — these are the public *shapes* of the vehicles,
seeded so a user can immediately match a profile and then extend/override with
their own real, sourced entries.

Everything here is a plain dict so it round-trips to YAML/JSON and merges with a
user catalog. Load order: built-in seed -> user file -> per-run overrides.

SCOPE: business / capital only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .core import DealflowError, _yaml_load


# --------------------------------------------------------------------------- #
# Seed catalog — public categories of defense / dual-use funding vehicles.
# Values are typical, unclassified ranges for matching heuristics, not quotes.
# --------------------------------------------------------------------------- #
SEED_SOURCES: list[dict[str, Any]] = [
    {
        "id": "sbir-phase-i",
        "name": "SBIR/STTR Phase I",
        "category": "non-dilutive-grant",
        "funds": "Feasibility studies for a proposed innovation with agency need.",
        "check_min": 50_000,
        "check_max": 314_000,
        "dilution": ["non-dilutive"],
        "capital_type": "non-dilutive",
        "timeline_months": 6,
        "stages": ["idea", "pre-seed", "seed"],
        "min_trl": 2,
        "thesis": ["dual-use", "deep-tech", "research"],
        "dual_use": ["dual-use", "pure-defense", "commercial"],
        "mandate": ["feasibility", "r&d", "small-business", "innovation"],
        "fit": "Earliest non-dilutive proof-of-concept money; small business only.",
    },
    {
        "id": "sbir-phase-ii",
        "name": "SBIR/STTR Phase II",
        "category": "non-dilutive-grant",
        "funds": "Prototype development building on a successful Phase I.",
        "check_min": 750_000,
        "check_max": 2_000_000,
        "dilution": ["non-dilutive"],
        "capital_type": "non-dilutive",
        "timeline_months": 24,
        "stages": ["seed", "series-a"],
        "min_trl": 4,
        "thesis": ["dual-use", "deep-tech", "prototype"],
        "dual_use": ["dual-use", "pure-defense", "commercial"],
        "mandate": ["prototype", "r&d", "small-business"],
        "fit": "Non-dilutive prototype capital; requires a completed Phase I.",
    },
    {
        "id": "sbir-phase-iii",
        "name": "SBIR Phase III / commercialization",
        "category": "non-dilutive-contract",
        "funds": "Transition of SBIR work into products/services on non-SBIR funds.",
        "check_min": 1_000_000,
        "check_max": 50_000_000,
        "dilution": ["non-dilutive"],
        "capital_type": "non-dilutive",
        "timeline_months": 36,
        "stages": ["series-a", "series-b", "growth"],
        "min_trl": 6,
        "thesis": ["transition", "production", "dual-use"],
        "dual_use": ["dual-use", "pure-defense"],
        "mandate": ["commercialization", "transition", "sole-source"],
        "fit": "Sole-source transition path for prior SBIR performers.",
    },
    {
        "id": "ota-prototype",
        "name": "OTA prototype agreement",
        "category": "other-transaction",
        "funds": "Rapid prototyping outside the FAR, often via a consortium.",
        "check_min": 250_000,
        "check_max": 100_000_000,
        "dilution": ["non-dilutive"],
        "capital_type": "non-dilutive",
        "timeline_months": 18,
        "stages": ["seed", "series-a", "series-b", "growth"],
        "min_trl": 4,
        "thesis": ["prototype", "dual-use", "rapid-acquisition"],
        "dual_use": ["dual-use", "pure-defense"],
        "mandate": ["prototype", "consortium", "non-traditional"],
        "fit": "Flexible, fast prototype vehicle; favors non-traditional contractors.",
    },
    {
        "id": "apfit",
        "name": "APFIT (Accelerate the Procurement and Fielding of Innovative Tech)",
        "category": "non-dilutive-transition",
        "funds": "Bridges the 'valley of death' by procuring late-stage prototypes.",
        "check_min": 10_000_000,
        "check_max": 50_000_000,
        "dilution": ["non-dilutive"],
        "capital_type": "non-dilutive",
        "timeline_months": 24,
        "stages": ["series-b", "growth", "late"],
        "min_trl": 7,
        "thesis": ["transition", "fielding", "dual-use"],
        "dual_use": ["dual-use", "pure-defense"],
        "mandate": ["fielding", "procurement", "valley-of-death"],
        "fit": "Late-TRL fielding capital for mature prototypes ready to scale.",
    },
    {
        "id": "defense-vc",
        "name": "Defense-focused venture capital",
        "category": "equity-vc",
        "funds": "Equity into dual-use and defense-tech startups.",
        "check_min": 500_000,
        "check_max": 30_000_000,
        "dilution": ["equity"],
        "capital_type": "equity",
        "timeline_months": 4,
        "stages": ["seed", "series-a", "series-b"],
        "min_trl": 3,
        "thesis": ["dual-use", "defense-tech", "national-security"],
        "dual_use": ["dual-use", "pure-defense", "commercial"],
        "mandate": ["scale", "product", "growth-equity"],
        "fit": "Patient equity comfortable with government sales cycles.",
    },
    {
        "id": "strategic-cvc",
        "name": "Strategic corporate VC (prime / OEM)",
        "category": "equity-strategic",
        "funds": "Equity plus commercial pull from a prime or OEM parent.",
        "check_min": 1_000_000,
        "check_max": 50_000_000,
        "dilution": ["equity", "convertible"],
        "capital_type": "equity",
        "timeline_months": 6,
        "stages": ["series-a", "series-b", "growth"],
        "min_trl": 5,
        "thesis": ["dual-use", "supply-chain", "strategic"],
        "dual_use": ["dual-use", "pure-defense", "commercial"],
        "mandate": ["strategic", "channel", "teaming"],
        "fit": "Money plus a route to a prime's programs; watch strategic lock-in.",
    },
    {
        "id": "iqt-style",
        "name": "Strategic non-profit investor (In-Q-Tel-style)",
        "category": "equity-strategic",
        "funds": "Mission-driven equity aligning startups to government end-users.",
        "check_min": 500_000,
        "check_max": 15_000_000,
        "dilution": ["equity", "convertible"],
        "capital_type": "equity",
        "timeline_months": 6,
        "stages": ["seed", "series-a", "series-b"],
        "min_trl": 4,
        "thesis": ["dual-use", "national-security", "deep-tech"],
        "dual_use": ["dual-use", "pure-defense"],
        "mandate": ["mission", "adoption", "pilot"],
        "fit": "Equity paired with an agency adoption pathway and pilots.",
    },
    {
        "id": "federal-grant",
        "name": "Federal research grant (non-SBIR)",
        "category": "non-dilutive-grant",
        "funds": "Basic/applied research grants (agency BAA, university-linked).",
        "check_min": 100_000,
        "check_max": 5_000_000,
        "dilution": ["non-dilutive"],
        "capital_type": "non-dilutive",
        "timeline_months": 18,
        "stages": ["idea", "pre-seed", "seed"],
        "min_trl": 1,
        "thesis": ["research", "deep-tech", "science"],
        "dual_use": ["dual-use", "commercial", "pure-defense"],
        "mandate": ["research", "baa", "university"],
        "fit": "Early research capital; strongest with an academic partner.",
    },
    {
        "id": "project-finance",
        "name": "Project finance / infrastructure debt",
        "category": "debt-project",
        "funds": "Non-recourse debt against a contracted revenue project.",
        "check_min": 5_000_000,
        "check_max": 500_000_000,
        "dilution": ["debt", "non-dilutive"],
        "capital_type": "debt",
        "timeline_months": 12,
        "stages": ["growth", "late", "public"],
        "min_trl": 8,
        "thesis": ["infrastructure", "energy", "manufacturing"],
        "dual_use": ["dual-use", "commercial"],
        "mandate": ["project", "capex", "contracted-revenue"],
        "fit": "Capital-project financing where a signed offtake de-risks debt.",
    },
    {
        "id": "growth-equity",
        "name": "Growth / late-stage equity",
        "category": "equity-growth",
        "funds": "Large equity rounds into companies with proven revenue.",
        "check_min": 10_000_000,
        "check_max": 200_000_000,
        "dilution": ["equity"],
        "capital_type": "equity",
        "timeline_months": 5,
        "stages": ["series-c", "growth", "late"],
        "min_trl": 8,
        "thesis": ["scale", "revenue", "dual-use"],
        "dual_use": ["dual-use", "commercial", "pure-defense"],
        "mandate": ["scale", "revenue", "expansion"],
        "fit": "Scale capital for companies past product-market fit.",
    },
    {
        "id": "venture-debt",
        "name": "Venture debt",
        "category": "debt-venture",
        "funds": "Debt to extend runway alongside an equity round.",
        "check_min": 500_000,
        "check_max": 25_000_000,
        "dilution": ["debt", "hybrid"],
        "capital_type": "debt",
        "timeline_months": 3,
        "stages": ["series-a", "series-b", "growth"],
        "min_trl": 5,
        "thesis": ["runway", "hardware", "dual-use"],
        "dual_use": ["dual-use", "commercial"],
        "mandate": ["runway", "non-dilutive-topup", "bridge"],
        "fit": "Runway extension with minimal dilution; needs an equity anchor.",
    },
]


@dataclass
class SourceCatalog:
    """A mutable, mergeable catalog of capital-source category dicts."""

    sources: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate(self.sources)

    @staticmethod
    def _validate(items: list[dict]) -> None:
        if not isinstance(items, list):
            raise DealflowError("capital-source catalog must be a list")
        seen: set[str] = set()
        for i, s in enumerate(items):
            if not isinstance(s, dict):
                raise DealflowError(f"source #{i} must be a mapping")
            sid = str(s.get("id") or s.get("name") or "").strip()
            if not sid:
                raise DealflowError(f"source #{i} must have an id or name")
            if sid in seen:
                raise DealflowError(f"duplicate capital-source id: {sid!r}")
            seen.add(sid)

    def ids(self) -> list[str]:
        return [str(s.get("id") or s.get("name")) for s in self.sources]

    def get(self, sid: str) -> dict:
        sid_n = str(sid).strip().lower()
        for s in self.sources:
            if str(s.get("id") or "").lower() == sid_n or str(s.get("name") or "").lower() == sid_n:
                return s
        raise DealflowError(f"unknown capital source: {sid!r}")

    def by_category(self, category: str) -> list[dict]:
        c = str(category).strip().lower()
        return [s for s in self.sources if str(s.get("category") or "").lower() == c]

    def categories(self) -> list[str]:
        return sorted({str(s.get("category") or "uncategorized") for s in self.sources})

    def merge(self, others: list[dict]) -> "SourceCatalog":
        """Return a new catalog with ``others`` overriding same-id entries."""
        self._validate(others)
        index = {str(s.get("id") or s.get("name")).lower(): dict(s) for s in self.sources}
        for o in others:
            index[str(o.get("id") or o.get("name")).lower()] = dict(o)
        return SourceCatalog(sources=list(index.values()))

    def to_dict(self) -> dict:
        return {"count": len(self.sources), "sources": self.sources}


def default_catalog() -> SourceCatalog:
    """The built-in seed catalog (a fresh copy each call)."""
    return SourceCatalog(sources=[dict(s) for s in SEED_SOURCES])


def load_catalog(path: str) -> SourceCatalog:
    """Load a user catalog from a YAML or JSON file (list, or {sources: [...]})."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    return parse_catalog(text)


def parse_catalog(text: str) -> SourceCatalog:
    text_stripped = text.lstrip()
    data: Any
    if text_stripped[:1] in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = _yaml_load(text)
    else:
        data = _yaml_load(text)
    if isinstance(data, dict):
        data = data.get("sources") or data.get("capital_sources") or []
    if not isinstance(data, list):
        raise DealflowError("catalog must be a list or a mapping with a 'sources' list")
    return SourceCatalog(sources=data)


def merged_catalog(user_path: str | None = None) -> SourceCatalog:
    """Seed catalog merged with an optional user file (user wins on id clash)."""
    cat = default_catalog()
    if user_path:
        user = load_catalog(user_path)
        cat = cat.merge(user.sources)
    return cat
