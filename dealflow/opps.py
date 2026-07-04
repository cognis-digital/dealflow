"""Opportunity pipeline tracker — capture pipeline for capital & teaming deals.

A lightweight, deterministic tracker for business-development *opportunities*
(a capital raise, a contract pursuit, a teaming pursuit) as they move through a
capture pipeline. Each opportunity has a stage, a value, and a win probability;
the tracker computes probability-weighted value and emits a **next-action
prompt** per opportunity based on its stage and staleness.

This complements the historical forecast engine in :mod:`dealflow.core` (which
reasons over a CSV event log) — here we track a *live* list of pursuits with
explicit per-deal probabilities and playbook-driven next actions.

Deterministic, offline, stdlib only.

SCOPE: business capture pipeline only.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from typing import Any

from .core import DealflowError, _yaml_load


# Default capture stages with a baseline win probability and a next-action
# playbook prompt. Users may override stages via a config file.
DEFAULT_STAGES: list[dict] = [
    {"name": "identified", "probability": 0.05, "action": "Qualify the requirement and confirm a real budget/authority."},
    {"name": "qualified", "probability": 0.15, "action": "Map decision-makers and shape the acquisition strategy."},
    {"name": "capture", "probability": 0.30, "action": "Build the team and refine the win theme; line up teaming partners."},
    {"name": "proposal", "probability": 0.50, "action": "Finalize the proposal and pricing; secure teaming agreements."},
    {"name": "submitted", "probability": 0.65, "action": "Prepare for orals/clarifications; hold the team ready."},
    {"name": "awarded", "probability": 1.00, "action": "Kick off; transition to program execution."},
    {"name": "lost", "probability": 0.00, "action": "Run a debrief and capture lessons for the next pursuit."},
]

STALE_DAYS_DEFAULT = 30


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _parse_date(s: Any) -> _dt.date | None:
    s = str(s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise DealflowError(f"unrecognized date: {s!r}")


@dataclass
class Opp:
    id: str
    name: str
    stage: str
    value: float = 0.0
    probability: float | None = None      # explicit override of stage baseline
    owner: str = ""
    updated: _dt.date | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Opp":
        if not isinstance(d, dict):
            raise DealflowError("opportunity must be a mapping")
        oid = str(d.get("id") or d.get("name") or "").strip()
        if not oid:
            raise DealflowError("opportunity must have an id or name")
        raw_val = d.get("value") or d.get("amount") or 0
        try:
            value = float(str(raw_val).replace("$", "").replace(",", "") or 0)
        except ValueError:
            raise DealflowError(f"opportunity {oid!r}: value {raw_val!r} not numeric") from None
        if value < 0:
            raise DealflowError(f"opportunity {oid!r}: value is negative")
        prob = d.get("probability", d.get("p_win"))
        if prob is not None and prob != "":
            try:
                prob = float(prob)
            except ValueError:
                raise DealflowError(f"opportunity {oid!r}: probability not numeric") from None
            if not 0.0 <= prob <= 1.0:
                raise DealflowError(f"opportunity {oid!r}: probability must be 0..1")
        else:
            prob = None
        tags = d.get("tags") or []
        if isinstance(tags, str):
            s = tags.strip()
            if s[:1] == "[" and s[-1:] == "]":
                s = s[1:-1]
            tags = [t.strip().strip("[]") for t in s.split(",") if t.strip().strip("[]")]
        return cls(
            id=oid,
            name=str(d.get("name") or oid),
            stage=_norm(d.get("stage") or "identified"),
            value=value,
            probability=prob,
            owner=str(d.get("owner") or ""),
            updated=_parse_date(d.get("updated") or d.get("last_updated")),
            tags=list(tags),
        )


@dataclass
class PipelineTracker:
    opps: list[Opp]
    stages: list[dict] = field(default_factory=lambda: [dict(s) for s in DEFAULT_STAGES])
    stale_days: int = STALE_DAYS_DEFAULT

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for o in self.opps:
            if o.id in seen:
                raise DealflowError(f"duplicate opportunity id: {o.id!r}")
            seen.add(o.id)
        self._stage_index = {_norm(s["name"]): s for s in self.stages}

    def _stage(self, name: str) -> dict:
        s = self._stage_index.get(_norm(name))
        if s is None:
            raise DealflowError(f"unknown stage: {name!r}")
        return s

    def probability(self, opp: Opp) -> float:
        if opp.probability is not None:
            return opp.probability
        return float(self._stage(opp.stage).get("probability", 0.0))

    def weighted_value(self, opp: Opp) -> float:
        return opp.value * self.probability(opp)

    def is_open(self, opp: Opp) -> bool:
        p = self.probability(opp)
        return 0.0 < p < 1.0

    def is_stale(self, opp: Opp, *, today: _dt.date | None = None) -> bool:
        if opp.updated is None or not self.is_open(opp):
            return False
        today = today or _dt.date.today()
        return (today - opp.updated).days > self.stale_days

    def next_action(self, opp: Opp, *, today: _dt.date | None = None) -> str:
        base = str(self._stage(opp.stage).get("action", "")).strip()
        if self.is_stale(opp, today=today):
            days = (((today or _dt.date.today()) - opp.updated).days) if opp.updated else 0
            return f"STALE ({days}d, no update): {base}"
        return base

    def summary(self, *, today: _dt.date | None = None) -> dict:
        rows = []
        total = weighted = won = lost = open_val = 0.0
        n_open = n_won = n_lost = 0
        for o in sorted(self.opps, key=lambda x: (-self.weighted_value(x), x.id)):
            p = self.probability(o)
            wv = self.weighted_value(o)
            status = "won" if p >= 1.0 else ("lost" if p <= 0.0 else "open")
            total += o.value
            if status == "open":
                weighted += wv
                open_val += o.value
                n_open += 1
            elif status == "won":
                won += o.value
                n_won += 1
            else:
                n_lost += 1
                lost += o.value
            rows.append({
                "id": o.id,
                "name": o.name,
                "stage": o.stage,
                "status": status,
                "value": round(o.value, 2),
                "probability": round(p, 4),
                "weighted_value": round(wv, 2),
                "owner": o.owner,
                "stale": self.is_stale(o, today=today),
                "next_action": self.next_action(o, today=today),
                "tags": o.tags,
            })
        stage_roll: dict[str, dict] = {}
        for o in self.opps:
            st = stage_roll.setdefault(o.stage, {"stage": o.stage, "count": 0, "value": 0.0, "weighted": 0.0})
            st["count"] += 1
            st["value"] = round(st["value"] + o.value, 2)
            st["weighted"] = round(st["weighted"] + self.weighted_value(o), 2)
        return {
            "total_opportunities": len(self.opps),
            "open": n_open,
            "won": n_won,
            "lost": n_lost,
            "open_value": round(open_val, 2),
            "won_value": round(won, 2),
            "weighted_pipeline": round(weighted, 2),
            "stages": [stage_roll[s["name"]] for s in self.stages if s["name"] in stage_roll],
            "opportunities": rows,
        }


def load_tracker(path: str, *, today: _dt.date | None = None) -> PipelineTracker:
    with open(path, "r", encoding="utf-8") as fh:
        return parse_tracker(fh.read())


def parse_tracker(text: str) -> PipelineTracker:
    text_stripped = text.lstrip()
    if text_stripped[:1] in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = _yaml_load(text)
    else:
        data = _yaml_load(text)
    stages = None
    stale_days = STALE_DAYS_DEFAULT
    if isinstance(data, dict):
        stages = data.get("stages")
        if data.get("stale_days") not in (None, ""):
            stale_days = int(data["stale_days"])
        items = data.get("opportunities") or data.get("opps") or data.get("pipeline") or []
    elif isinstance(data, list):
        items = data
    else:
        raise DealflowError("pipeline file must be a list or a mapping")
    opps = [Opp.from_dict(d) for d in items]
    kwargs: dict = {"opps": opps, "stale_days": stale_days}
    if isinstance(stages, list) and stages:
        norm_stages = []
        for s in stages:
            if isinstance(s, str):
                norm_stages.append({"name": s, "probability": 0.0, "action": ""})
            elif isinstance(s, dict) and s.get("name"):
                norm_stages.append({
                    "name": s["name"],
                    "probability": float(s.get("probability", 0.0)),
                    "action": str(s.get("action", "")),
                })
            else:
                raise DealflowError(f"bad stage definition: {s!r}")
        kwargs["stages"] = norm_stages
    return PipelineTracker(**kwargs)
