"""Strategic teaming — model a teaming graph and recommend arrangements.

Given a roster of organizations (primes, subs, small businesses) with their
capabilities, set-aside status, and past-performance tags, and a target
*opportunity* with required capabilities and set-aside preferences, this module:

* builds a teaming graph (who can complement whom),
* recommends a team that covers the opportunity's required capabilities,
* runs a **gap analysis** — which requirements are still uncovered and which
  set-aside goals are unmet,
* scores candidate subcontractors by how much *new* capability + past
  performance they add to a partial team (marginal coverage).

Deterministic, offline, stdlib only. Set-aside categories model the public U.S.
small-business programs (8(a), SDVOSB, HUBZone, WOSB, VOSB, small-business).

SCOPE: business teaming / capture strategy only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import DealflowError


# Public small-business set-aside program codes.
SET_ASIDES = {
    "8(a)": "8(a) Business Development",
    "sdvosb": "Service-Disabled Veteran-Owned Small Business",
    "vosb": "Veteran-Owned Small Business",
    "hubzone": "Historically Underutilized Business Zone",
    "wosb": "Women-Owned Small Business",
    "edwosb": "Economically Disadvantaged Women-Owned Small Business",
    "small-business": "Small Business",
}

ROLE_KINDS = {"prime", "sub", "small-business", "supplier", "academic", "any"}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _as_set(v: Any) -> set[str]:
    """Coerce a scalar / list / comma-string into a normalized token set.

    Tolerates an inline flow-sequence string ``"[a, b]"`` from the minimal YAML
    parser by stripping the surrounding brackets.
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


@dataclass
class Org:
    id: str
    name: str
    role: str = "sub"                       # prime / sub / small-business / ...
    capabilities: set[str] = field(default_factory=set)
    set_asides: set[str] = field(default_factory=set)
    past_performance: set[str] = field(default_factory=set)
    clearance: str = ""                     # e.g. "secret", "ts-sci" (opaque token)

    @classmethod
    def from_dict(cls, d: dict) -> "Org":
        if not isinstance(d, dict):
            raise DealflowError("org must be a mapping")
        oid = str(d.get("id") or d.get("name") or "").strip()
        if not oid:
            raise DealflowError("org must have an id or name")
        role = _norm(d.get("role") or "sub")
        return cls(
            id=oid,
            name=str(d.get("name") or oid),
            role=role,
            capabilities=_as_set(d.get("capabilities")) | _as_set(d.get("caps")),
            set_asides={_norm(x) for x in _as_set(d.get("set_asides")) | _as_set(d.get("set_aside"))},
            past_performance=_as_set(d.get("past_performance")) | _as_set(d.get("pp")),
            clearance=_norm(d.get("clearance")),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "capabilities": sorted(self.capabilities),
            "set_asides": sorted(self.set_asides),
            "past_performance": sorted(self.past_performance),
            "clearance": self.clearance,
        }


@dataclass
class Opportunity:
    name: str
    required_capabilities: set[str] = field(default_factory=set)
    preferred_capabilities: set[str] = field(default_factory=set)
    set_aside_goals: set[str] = field(default_factory=set)   # desired set-asides on the team
    clearance: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Opportunity":
        if not isinstance(d, dict):
            raise DealflowError("opportunity must be a mapping")
        return cls(
            name=str(d.get("name") or "opportunity"),
            required_capabilities=_as_set(d.get("required_capabilities")) | _as_set(d.get("required")),
            preferred_capabilities=_as_set(d.get("preferred_capabilities")) | _as_set(d.get("preferred")),
            set_aside_goals={_norm(x) for x in _as_set(d.get("set_aside_goals")) | _as_set(d.get("set_asides"))},
            clearance=_norm(d.get("clearance")),
        )


@dataclass
class TeamingGraph:
    """A roster plus the complementary-capability edges between organizations."""

    orgs: list[Org]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for o in self.orgs:
            if o.id in seen:
                raise DealflowError(f"duplicate org id: {o.id!r}")
            seen.add(o.id)
        self._index = {o.id: o for o in self.orgs}

    @classmethod
    def from_dicts(cls, items: list[dict]) -> "TeamingGraph":
        if not isinstance(items, list):
            raise DealflowError("roster must be a list of orgs")
        return cls(orgs=[Org.from_dict(d) for d in items])

    def get(self, oid: str) -> Org:
        o = self._index.get(oid) or self._index.get(str(oid))
        if o is None:
            # fall back to case-insensitive name/id match
            n = _norm(oid)
            for org in self.orgs:
                if _norm(org.id) == n or _norm(org.name) == n:
                    return org
            raise DealflowError(f"unknown org: {oid!r}")
        return o

    def complements(self, oid: str, *, min_new: int = 1) -> list[tuple[Org, set[str]]]:
        """Orgs that bring capabilities ``oid`` lacks (complementary edges).

        Returns (org, new_capabilities) sorted by how much new capability each
        adds. This is the teaming graph's adjacency, computed on demand.
        """
        base = self.get(oid)
        out = []
        for other in self.orgs:
            if other.id == base.id:
                continue
            new = other.capabilities - base.capabilities
            if len(new) >= min_new:
                out.append((other, new))
        out.sort(key=lambda t: (len(t[1]), len(t[0].past_performance)), reverse=True)
        return out

    def edges(self, *, min_new: int = 1) -> list[dict]:
        """All complementary edges as serializable records (for reports/graphs)."""
        seen: set[tuple[str, str]] = set()
        out = []
        for a in self.orgs:
            for b, new in self.complements(a.id, min_new=min_new):
                key = tuple(sorted((a.id, b.id)))
                if key in seen:
                    continue
                seen.add(key)
                mutual = b.capabilities - a.capabilities
                back = a.capabilities - b.capabilities
                out.append({
                    "a": a.id, "b": b.id,
                    "a_adds": sorted(back), "b_adds": sorted(mutual),
                    "complementarity": len(back | mutual),
                })
        out.sort(key=lambda e: e["complementarity"], reverse=True)
        return out


@dataclass
class TeamRecommendation:
    opportunity: str
    prime: str | None
    members: list[str]
    covered: set[str]
    uncovered: set[str]
    preferred_covered: set[str]
    set_asides_met: set[str]
    set_asides_missing: set[str]
    coverage: float               # required-capability coverage, 0..1
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "opportunity": self.opportunity,
            "prime": self.prime,
            "members": self.members,
            "covered": sorted(self.covered),
            "uncovered": sorted(self.uncovered),
            "preferred_covered": sorted(self.preferred_covered),
            "set_asides_met": sorted(self.set_asides_met),
            "set_asides_missing": sorted(self.set_asides_missing),
            "coverage": round(self.coverage, 4),
            "complete": not self.uncovered and not self.set_asides_missing,
            "rationale": self.rationale,
        }


def gap_analysis(team: list[Org], opp: Opportunity) -> dict:
    """Which required capabilities and set-aside goals a given team leaves open."""
    team_caps: set[str] = set()
    team_sa: set[str] = set()
    for o in team:
        team_caps |= o.capabilities
        team_sa |= o.set_asides
    covered = opp.required_capabilities & team_caps
    uncovered = opp.required_capabilities - team_caps
    pref_cov = opp.preferred_capabilities & team_caps
    sa_met = opp.set_aside_goals & team_sa
    sa_missing = opp.set_aside_goals - team_sa
    req = len(opp.required_capabilities)
    coverage = (len(covered) / req) if req else 1.0
    return {
        "covered": covered,
        "uncovered": uncovered,
        "preferred_covered": pref_cov,
        "set_asides_met": sa_met,
        "set_asides_missing": sa_missing,
        "coverage": coverage,
    }


def _marginal(org: Org, opp: Opportunity, have_caps: set[str], have_sa: set[str]) -> tuple[int, int, int]:
    """Value org adds to a partial team: (new required, new set-aside, new preferred)."""
    new_req = len((opp.required_capabilities & org.capabilities) - have_caps)
    new_sa = len((opp.set_aside_goals & org.set_asides) - have_sa)
    new_pref = len((opp.preferred_capabilities & org.capabilities) - have_caps)
    return new_req, new_sa, new_pref


def recommend_team(
    graph: TeamingGraph,
    opp: Opportunity,
    *,
    prime: str | None = None,
    max_members: int = 6,
) -> TeamRecommendation:
    """Greedily assemble a team that covers the opportunity's requirements.

    Strategy: start from a prime (given, or the org covering the most required
    capabilities), then repeatedly add the org with the highest marginal value
    (new required capability first, then unmet set-aside, then preferred). Stops
    when everything is covered or ``max_members`` is reached. Deterministic:
    ties break on past-performance count, then id.
    """
    if not graph.orgs:
        raise DealflowError("teaming graph is empty")

    def pick_prime() -> Org:
        if prime is not None:
            return graph.get(prime)
        ranked = sorted(
            graph.orgs,
            key=lambda o: (
                len(opp.required_capabilities & o.capabilities),
                1 if o.role == "prime" else 0,
                len(o.past_performance),
                o.id,
            ),
            reverse=True,
        )
        return ranked[0]

    lead = pick_prime()
    team = [lead]
    rationale = [
        f"prime {lead.name!r} covers "
        f"{len(opp.required_capabilities & lead.capabilities)}/"
        f"{len(opp.required_capabilities)} required capabilities"
    ]
    have_caps = set(lead.capabilities)
    have_sa = set(lead.set_asides)

    while len(team) < max_members:
        ga = gap_analysis(team, opp)
        if not ga["uncovered"] and not ga["set_asides_missing"]:
            break
        candidates = [o for o in graph.orgs if o.id not in {t.id for t in team}]
        best = None
        best_key = (0, 0, 0)
        for o in candidates:
            key = _marginal(o, opp, have_caps, have_sa)
            if key > best_key or (
                key == best_key and best is not None
                and (len(o.past_performance), o.id) > (len(best.past_performance), best.id)
            ):
                if sum(key) > 0:
                    best, best_key = o, key
        if best is None:
            break
        team.append(best)
        added_req = sorted((opp.required_capabilities & best.capabilities) - have_caps)
        added_sa = sorted((opp.set_aside_goals & best.set_asides) - have_sa)
        have_caps |= best.capabilities
        have_sa |= best.set_asides
        bits = []
        if added_req:
            bits.append(f"required: {', '.join(added_req)}")
        if added_sa:
            bits.append(f"set-aside: {', '.join(added_sa)}")
        rationale.append(f"add {best.name!r} -> " + "; ".join(bits or ["preferred capability"]))

    ga = gap_analysis(team, opp)
    return TeamRecommendation(
        opportunity=opp.name,
        prime=lead.id,
        members=[o.id for o in team],
        covered=ga["covered"],
        uncovered=ga["uncovered"],
        preferred_covered=ga["preferred_covered"],
        set_asides_met=ga["set_asides_met"],
        set_asides_missing=ga["set_asides_missing"],
        coverage=ga["coverage"],
        rationale=rationale,
    )
