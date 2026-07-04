"""Capital matchmaking — transparent, explainable fit scoring.

Given a *company / technology profile* and a *capital source profile*, compute a
0-100 fit score built from named, weighted factors. Every score ships with its
full factor breakdown: which factors contributed, how much, and why. There is no
black box — the same inputs always produce the same score, and the breakdown
reconciles to the total.

Design goals
------------
* **Explainable.** The output is a list of ``FactorScore`` (name, weight, raw
  0-1 match, weighted contribution, human-readable reason), not a single opaque
  number.
* **Deterministic & offline.** Pure Python, no network, no randomness. Same
  inputs -> same output.
* **Graceful degradation.** Missing profile fields never crash; a factor with
  no data to compare simply abstains (weight redistributed across the factors
  that *can* be evaluated), and the reason records that it abstained.

Profiles are plain dicts (from YAML/JSON/CLI) so the engine stays substrate
agnostic. See :mod:`dealflow.capital_sources` for the funding-vehicle taxonomy
that supplies typical ``CapitalSource`` shapes.

SCOPE: business / capital / teaming only. Nothing here touches weapons,
targeting, or operational capability — it maps money to companies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .core import DealflowError


# --------------------------------------------------------------------------- #
# Vocabulary — the canonical stage / dilution / mandate ladders. Kept liberal:
# unknown values are normalized (lower/trim) and compared as opaque tokens so a
# user's custom stage still matches itself.
# --------------------------------------------------------------------------- #
STAGE_LADDER = [
    "idea", "pre-seed", "seed", "series-a", "series-b",
    "series-c", "growth", "late", "public",
]

# Canonical synonyms folded onto the ladder above.
_STAGE_ALIASES = {
    "preseed": "pre-seed", "pre seed": "pre-seed",
    "a": "series-a", "b": "series-b", "c": "series-c",
    "seriesa": "series-a", "seriesb": "series-b", "seriesc": "series-c",
    "early": "seed", "mezzanine": "late", "pre-ipo": "late", "ipo": "public",
}

DILUTION_KINDS = {"non-dilutive", "equity", "convertible", "debt", "hybrid"}
DUAL_USE_KINDS = {"pure-defense", "dual-use", "commercial"}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _norm_stage(s: Any) -> str:
    t = _norm(s).replace("_", "-")
    # fold a space-separated form ("series a") onto the alias/ladder form first,
    # then the hyphenated form ("series-a").
    if t in _STAGE_ALIASES:
        return _STAGE_ALIASES[t]
    t = t.replace(" ", "-")
    return _STAGE_ALIASES.get(t, t)


def _as_set(v: Any) -> set[str]:
    """Coerce a scalar / list / comma-string into a normalized set of tokens.

    Tolerates an inline flow-sequence string like ``"[a, b, c]"`` (which the
    minimal YAML subset parser hands back verbatim) by stripping the brackets.
    """
    if v is None:
        return set()
    if isinstance(v, (list, tuple, set)):
        items = v
    else:
        s = str(v).strip()
        if s[:1] == "[" and s[-1:] == "]":
            s = s[1:-1]
        items = s.split(",")
    return {_norm(str(x).strip().strip("[]")) for x in items if _norm(str(x).strip().strip("[]"))}


# --------------------------------------------------------------------------- #
# Explainable factor result
# --------------------------------------------------------------------------- #
@dataclass
class FactorScore:
    name: str
    weight: float          # configured importance (relative)
    raw: float | None      # 0..1 match strength, or None when the factor abstained
    reason: str            # human-readable explanation

    @property
    def abstained(self) -> bool:
        return self.raw is None

    @property
    def contribution(self) -> float:
        """Effective 0..1 contribution (0 while abstaining, before renormalizing)."""
        return 0.0 if self.raw is None else self.raw

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "weight": round(self.weight, 4),
            "raw": None if self.raw is None else round(self.raw, 4),
            "abstained": self.abstained,
            "reason": self.reason,
        }


@dataclass
class MatchResult:
    company: str
    source: str
    score: float                      # 0..100
    factors: list[FactorScore]
    effective_weight: float           # sum of weights of non-abstaining factors
    source_meta: dict = field(default_factory=dict)

    @property
    def band(self) -> str:
        if self.score >= 80:
            return "strong"
        if self.score >= 60:
            return "promising"
        if self.score >= 40:
            return "possible"
        return "weak"

    def top_factors(self, n: int = 3) -> list[FactorScore]:
        live = [f for f in self.factors if not f.abstained]
        return sorted(live, key=lambda f: f.weight * (f.raw or 0.0), reverse=True)[:n]

    def gaps(self) -> list[FactorScore]:
        """Live factors that scored poorly (< 0.5) — the reasons this isn't higher."""
        return sorted(
            [f for f in self.factors if not f.abstained and (f.raw or 0.0) < 0.5],
            key=lambda f: f.weight * (1.0 - (f.raw or 0.0)),
            reverse=True,
        )

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "source": self.source,
            "score": round(self.score, 2),
            "band": self.band,
            "effective_weight": round(self.effective_weight, 4),
            "factors": [f.to_dict() for f in self.factors],
            "source_meta": self.source_meta,
        }


# --------------------------------------------------------------------------- #
# Factor library — each returns (raw 0..1 or None, reason)
# --------------------------------------------------------------------------- #
FactorFn = Callable[[dict, dict], "tuple[float | None, str]"]


def _f_stage(company: dict, source: dict) -> tuple[float | None, str]:
    """How close is the company's stage to what the source funds?"""
    cs = _norm_stage(company.get("stage"))
    stages = {_norm_stage(x) for x in _as_set(source.get("stages"))}
    if not cs or not stages:
        return None, "no stage data on one side"
    if cs in stages:
        return 1.0, f"stage {cs!r} is directly in the source's mandate"
    # Adjacent on the ladder scores partial; farther = lower.
    if cs in STAGE_LADDER:
        ci = STAGE_LADDER.index(cs)
        dists = [abs(ci - STAGE_LADDER.index(s)) for s in stages if s in STAGE_LADDER]
        if dists:
            d = min(dists)
            raw = max(0.0, 1.0 - d * 0.34)
            return raw, f"stage {cs!r} is {d} step(s) from the source's range"
    return 0.2, f"stage {cs!r} not in source's stated stages"


def _f_check_size(company: dict, source: dict) -> tuple[float | None, str]:
    """Does the ask fit inside the source's check-size band?"""
    ask = company.get("ask") or company.get("raise") or company.get("check_size")
    lo = source.get("check_min")
    hi = source.get("check_max")
    try:
        ask = None if ask in (None, "") else float(ask)
        lo = None if lo in (None, "") else float(lo)
        hi = None if hi in (None, "") else float(hi)
    except (TypeError, ValueError):
        return None, "check-size values not numeric"
    if ask is None or (lo is None and hi is None):
        return None, "no check-size data to compare"
    lo = lo if lo is not None else 0.0
    hi = hi if hi is not None else float("inf")
    if lo <= ask <= hi:
        return 1.0, f"ask ${ask:,.0f} fits the source's ${lo:,.0f}-{_cap(hi)} band"
    # Outside the band: how far, log-ish tolerance.
    if ask < lo:
        ratio = ask / lo if lo else 0.0
        raw = max(0.0, min(1.0, ratio))
        return raw, f"ask ${ask:,.0f} below the source's ${lo:,.0f} minimum"
    ratio = hi / ask if ask else 0.0
    raw = max(0.0, min(1.0, ratio))
    return raw, f"ask ${ask:,.0f} above the source's {_cap(hi)} maximum"


def _cap(hi: float) -> str:
    return "∞" if hi == float("inf") else f"${hi:,.0f}"


def _f_sector(company: dict, source: dict) -> tuple[float | None, str]:
    """Jaccard overlap of company sectors/tech vs. source thesis sectors."""
    c = _as_set(company.get("sectors")) | _as_set(company.get("technology"))
    s = _as_set(source.get("thesis")) | _as_set(source.get("sectors"))
    if not c or not s:
        return None, "no sector/thesis data to compare"
    inter = c & s
    union = c | s
    raw = len(inter) / len(union) if union else 0.0
    if inter:
        return raw, f"shared thesis: {', '.join(sorted(inter))}"
    return 0.0, "no overlapping sectors with source thesis"


def _f_geography(company: dict, source: dict) -> tuple[float | None, str]:
    """Is the company inside the source's geographic mandate?"""
    c = _as_set(company.get("geography")) | _as_set(company.get("country")) | _as_set(company.get("region"))
    s = _as_set(source.get("geography")) | _as_set(source.get("regions"))
    if not c or not s:
        return None, "no geography data to compare"
    if "global" in s or "any" in s or "worldwide" in s:
        return 1.0, "source invests globally"
    inter = c & s
    if inter:
        return 1.0, f"geography match: {', '.join(sorted(inter))}"
    return 0.1, f"company geography {sorted(c)} outside source's {sorted(s)}"


def _f_mandate(company: dict, source: dict) -> tuple[float | None, str]:
    """Free-text mandate keyword overlap (mission fit)."""
    c = _as_set(company.get("keywords")) | _as_set(company.get("mission"))
    s = _as_set(source.get("mandate")) | _as_set(source.get("keywords"))
    if not c or not s:
        return None, "no mandate keywords to compare"
    inter = c & s
    raw = len(inter) / max(1, len(s))
    if inter:
        return min(1.0, raw + 0.2), f"mandate keywords matched: {', '.join(sorted(inter))}"
    return 0.0, "no mandate keyword overlap"


def _f_dilution(company: dict, source: dict) -> tuple[float | None, str]:
    """Does the company's dilution preference match what the source offers?"""
    want = _norm(company.get("dilution_pref") or company.get("dilution"))
    give = _as_set(source.get("dilution")) or {_norm(source.get("capital_type"))} - {""}
    if not want or not give:
        return None, "no dilution preference / offering to compare"
    if want in give:
        return 1.0, f"source offers {want!r} capital as preferred"
    # Non-dilutive seekers strongly dislike equity and vice-versa.
    if want == "non-dilutive" and "non-dilutive" not in give:
        return 0.1, "company wants non-dilutive; source is dilutive"
    if want == "equity" and give <= {"non-dilutive"}:
        return 0.4, "company open to equity; source is non-dilutive only"
    return 0.5, f"partial dilution fit ({want!r} vs {sorted(give)})"


def _f_dual_use(company: dict, source: dict) -> tuple[float | None, str]:
    """Pure-defense vs dual-use vs commercial alignment."""
    c = _norm(company.get("dual_use") or company.get("posture"))
    s = _as_set(source.get("dual_use")) or _as_set(source.get("posture"))
    if not c or not s:
        return None, "no dual-use posture to compare"
    if c in s or "any" in s:
        return 1.0, f"posture {c!r} matches source appetite"
    # dual-use is a bridge — partial credit to either pure-defense or commercial.
    if c == "dual-use" or "dual-use" in s:
        return 0.6, f"dual-use bridges to source posture {sorted(s)}"
    return 0.2, f"posture {c!r} misaligned with source {sorted(s)}"


def _f_readiness(company: dict, source: dict) -> tuple[float | None, str]:
    """TRL / readiness vs. the source's minimum expected readiness (1-9)."""
    trl = company.get("trl") or company.get("readiness")
    need = source.get("min_trl")
    try:
        trl = None if trl in (None, "") else int(trl)
        need = None if need in (None, "") else int(need)
    except (TypeError, ValueError):
        return None, "TRL values not integers"
    if trl is None or need is None:
        return None, "no TRL data to compare"
    if trl >= need:
        return 1.0, f"TRL {trl} meets the source's minimum TRL {need}"
    gap = need - trl
    raw = max(0.0, 1.0 - gap * 0.25)
    return raw, f"TRL {trl} is {gap} below the source's minimum TRL {need}"


# Default factor registry. Weights are relative importance; they need not sum to
# 1 (they are renormalized over the factors that actually evaluate).
DEFAULT_FACTORS: dict[str, tuple[float, FactorFn]] = {
    "stage": (1.5, _f_stage),
    "check_size": (1.3, _f_check_size),
    "sector": (2.0, _f_sector),
    "geography": (0.8, _f_geography),
    "mandate": (1.2, _f_mandate),
    "dilution": (1.0, _f_dilution),
    "dual_use": (1.1, _f_dual_use),
    "readiness": (0.7, _f_readiness),
}


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def score_match(
    company: dict,
    source: dict,
    *,
    weights: dict[str, float] | None = None,
    factors: dict[str, tuple[float, FactorFn]] | None = None,
) -> MatchResult:
    """Score one company against one capital source, fully explainably.

    ``weights`` optionally overrides per-factor weights by name. ``factors``
    optionally supplies a custom registry (advanced). Abstaining factors are
    excluded from the denominator so a sparse profile is scored only on what it
    provides, never penalized for silence.
    """
    if not isinstance(company, dict) or not isinstance(source, dict):
        raise DealflowError("company and source profiles must be mappings")
    registry = dict(factors or DEFAULT_FACTORS)
    if weights:
        for name, w in weights.items():
            if name in registry:
                _, fn = registry[name]
                registry[name] = (float(w), fn)

    results: list[FactorScore] = []
    for name, (weight, fn) in registry.items():
        try:
            raw, reason = fn(company, source)
        except Exception as exc:  # a bad factor never sinks the whole score
            raw, reason = None, f"factor error, abstained: {exc}"
        results.append(FactorScore(name=name, weight=float(weight), raw=raw, reason=reason))

    live = [f for f in results if not f.abstained]
    eff_w = sum(f.weight for f in live)
    if eff_w <= 0:
        score = 0.0
    else:
        score = 100.0 * sum(f.weight * (f.raw or 0.0) for f in live) / eff_w

    return MatchResult(
        company=str(company.get("name") or company.get("id") or "company"),
        source=str(source.get("name") or source.get("id") or "source"),
        score=score,
        factors=results,
        effective_weight=eff_w,
        source_meta={
            "category": source.get("category"),
            "check_min": source.get("check_min"),
            "check_max": source.get("check_max"),
        },
    )


def rank_matches(
    company: dict,
    sources: list[dict],
    *,
    weights: dict[str, float] | None = None,
    top: int | None = None,
    min_score: float = 0.0,
) -> list[MatchResult]:
    """Score a company against many sources; return ranked, filtered results."""
    if not isinstance(sources, list):
        raise DealflowError("sources must be a list of source profiles")
    scored = [score_match(company, s, weights=weights) for s in sources]
    scored = [m for m in scored if m.score >= min_score]
    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:top] if top else scored


def explain(match: MatchResult) -> str:
    """Render a compact, human-readable explanation of a single match."""
    lines = [
        f"{match.company}  ×  {match.source}",
        f"  fit: {match.score:.0f}/100  ({match.band})",
        "  factors:",
    ]
    for f in sorted(match.factors, key=lambda x: x.weight, reverse=True):
        if f.abstained:
            lines.append(f"    - {f.name:<12} (w={f.weight:.1f})  --   {f.reason}")
        else:
            lines.append(
                f"    - {f.name:<12} (w={f.weight:.1f})  {f.raw * 100:>3.0f}%  {f.reason}"
            )
    return "\n".join(lines)
