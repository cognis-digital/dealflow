"""Core engine for DEALFLOW.

A pipeline is a directed state machine of stages. Deals move from stage to
stage over time (recorded in a CSV event log). DEALFLOW computes, per stage:

  * count of deals that ever entered the stage
  * stage->next conversion rate (advance rate)
  * average time-in-stage (velocity, in days)
  * win/loss outcomes

and produces a weighted-pipeline forecast: for every deal still open, the
expected value = amount * P(win | current stage), where P(win | stage) is the
product of historical advance rates from the current stage through to the won
stage.

No third-party dependencies: includes a small, deliberately-restricted YAML
subset parser sufficient for pipeline definitions.
"""
from __future__ import annotations

import csv
import io
import os
import datetime as _dt
from dataclasses import dataclass, field
from typing import Any


class DealflowError(Exception):
    """Raised on malformed pipeline definitions or deal logs."""


# --------------------------------------------------------------------------- #
# Identity — single source of truth is the repo VERSION file (falls back to a
# baked constant when the file isn't shipped, e.g. an installed wheel).
# --------------------------------------------------------------------------- #
TOOL_NAME = "dealflow"


def _read_version() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (
        os.path.join(here, os.pardir, "VERSION"),
        os.path.join(here, "VERSION"),
    ):
        try:
            with open(cand, "r", encoding="utf-8") as fh:
                v = fh.read().strip()
            if v:
                return v
        except OSError:
            continue
    return "0.0.0"


TOOL_VERSION = _read_version()


# --------------------------------------------------------------------------- #
# Minimal YAML subset parser (stdlib only)
# --------------------------------------------------------------------------- #
# Supports the subset needed for pipeline files:
#   key: value
#   key:
#     - item
#     - item
#   nested mappings via indentation
#   lists of mappings ("- key: value")
# Quotes (single/double) are stripped. '#' starts a comment.

def _strip_comment(line: str) -> str:
    out = []
    quote = None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out)


def _parse_flow_mapping(v: str) -> dict:
    """Parse a single-line flow mapping: ``{name: lost, type: lost}``.

    Deliberately small: comma-separated ``key: value`` pairs, quotes stripped,
    values coerced. Nested braces/brackets are not supported and raise.
    """
    inner = v[1:-1].strip()
    out: dict[str, Any] = {}
    if not inner:
        return out
    for part in inner.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise DealflowError(f"malformed flow mapping entry: {part!r}")
        k, _, val = part.partition(":")
        k = k.strip().strip("\"'")
        if not k:
            raise DealflowError(f"flow mapping has empty key in: {v!r}")
        out[k] = _coerce(val) if val.strip() else None
    return out


def _coerce(val: str) -> Any:
    v = val.strip()
    if not v:
        return None
    if v[0] == "{" and v[-1] == "}":
        return _parse_flow_mapping(v)
    if (v[0] == v[-1]) and v[0] in "\"'" and len(v) >= 2:
        return v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", "none"):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _yaml_load(text: str) -> Any:
    # Tokenize into (indent, content) ignoring blank/comment-only lines.
    raw_lines = text.splitlines()
    tokens = []
    for ln in raw_lines:
        ln = _strip_comment(ln.rstrip())
        if not ln.strip():
            continue
        if "\t" in (ln[: len(ln) - len(ln.lstrip())]):
            raise DealflowError("tabs not allowed for indentation in YAML")
        indent = len(ln) - len(ln.lstrip(" "))
        tokens.append((indent, ln.strip()))

    pos = 0

    def parse_block(min_indent: int):
        nonlocal pos
        if pos >= len(tokens):
            return None
        indent, content = tokens[pos]
        if content.startswith("- ") or content == "-":
            return parse_list(indent)
        return parse_map(indent)

    def parse_list(indent: int):
        nonlocal pos
        items = []
        while pos < len(tokens):
            cur_indent, content = tokens[pos]
            if cur_indent != indent or not (content.startswith("- ") or content == "-"):
                break
            pos += 1
            inner = content[1:].strip()
            if not inner:
                # nested block belongs to this list item
                child = parse_block(indent + 1) if pos < len(tokens) and tokens[pos][0] > indent else None
                items.append(child)
            elif inner[0] == "{" and inner[-1] == "}":
                # inline flow mapping: "- {name: lost, type: lost}"
                items.append(_parse_flow_mapping(inner))
            elif ":" in inner and not _looks_scalar(inner):
                # "- key: value" -> a mapping starting on the dash line.
                key, _, val = inner.partition(":")
                m = {key.strip(): _coerce(val) if val.strip() else None}
                # continuation lines indented further than the dash content
                content_indent = indent + 2
                while pos < len(tokens) and tokens[pos][0] >= content_indent and not (
                    tokens[pos][1].startswith("- ") and tokens[pos][0] == indent
                ):
                    sub = parse_map(tokens[pos][0])
                    if isinstance(sub, dict):
                        m.update(sub)
                    break
                if val.strip() == "" and pos < len(tokens) and tokens[pos][0] > indent:
                    m[key.strip()] = parse_block(tokens[pos][0])
                items.append(m)
            else:
                items.append(_coerce(inner))
        return items

    def parse_map(indent: int):
        nonlocal pos
        mapping = {}
        while pos < len(tokens):
            cur_indent, content = tokens[pos]
            if cur_indent != indent:
                break
            if content.startswith("- ") or content == "-":
                break
            if ":" not in content:
                raise DealflowError(f"expected 'key: value', got: {content!r}")
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            pos += 1
            if val:
                mapping[key] = _coerce(val)
            else:
                if pos < len(tokens) and tokens[pos][0] > indent:
                    mapping[key] = parse_block(tokens[pos][0])
                else:
                    mapping[key] = None
        return mapping

    def _looks_scalar(s: str) -> bool:
        # treat "http://x" etc as scalar; only the FIRST colon matters and a
        # mapping key shouldn't contain spaces before the colon in normal use.
        head = s.split(":", 1)[0]
        return " " in head and not head.replace(" ", "").isalnum()

    result = parse_block(0)
    return result if result is not None else {}


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Stage:
    name: str
    order: int
    terminal: bool = False      # terminal stage (won or lost)
    won: bool = False           # terminal-and-success


@dataclass
class Pipeline:
    name: str
    stages: list[Stage]
    won_stage: str
    lost_stages: set[str] = field(default_factory=set)

    def stage(self, name: str) -> Stage:
        for s in self.stages:
            if s.name == name:
                return s
        raise DealflowError(f"unknown stage: {name!r}")

    @property
    def open_stages(self) -> list[Stage]:
        return [s for s in self.stages if not s.terminal]

    def index(self, name: str) -> int:
        return self.stage(name).order


@dataclass
class Deal:
    deal_id: str
    amount: float
    history: list[tuple[str, _dt.date]]  # (stage, date) in chronological order

    @property
    def current_stage(self) -> str:
        return self.history[-1][0]


@dataclass
class Report:
    pipeline: str
    total_deals: int
    open_deals: int
    won_deals: int
    lost_deals: int
    open_value: float
    won_value: float
    weighted_forecast: float
    overall_win_rate: float
    stages: list[dict]
    deals: list[dict]

    def to_dict(self) -> dict:
        return {
            "pipeline": self.pipeline,
            "total_deals": self.total_deals,
            "open_deals": self.open_deals,
            "won_deals": self.won_deals,
            "lost_deals": self.lost_deals,
            "open_value": round(self.open_value, 2),
            "won_value": round(self.won_value, 2),
            "weighted_forecast": round(self.weighted_forecast, 2),
            "overall_win_rate": round(self.overall_win_rate, 4),
            "stages": self.stages,
            "deals": self.deals,
        }


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def parse_pipeline(text: str) -> Pipeline:
    data = _yaml_load(text)
    if not isinstance(data, dict):
        raise DealflowError("pipeline file must be a mapping at the top level")
    name = str(data.get("name") or "pipeline")
    raw_stages = data.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise DealflowError("pipeline must define a non-empty 'stages' list")

    stages: list[Stage] = []
    won_stage = None
    lost_stages: set[str] = set()
    seen_names: set[str] = set()
    won_count = 0
    for i, item in enumerate(raw_stages):
        if isinstance(item, str):
            sname, terminal, won = item, False, False
        elif isinstance(item, dict):
            sname = item.get("name")
            if not sname:
                raise DealflowError(f"stage #{i} missing 'name'")
            stype = str(item.get("type", "open")).lower()
            won = stype == "won" or bool(item.get("won"))
            terminal = won or stype in ("lost", "closed", "terminal") or bool(item.get("terminal"))
        else:
            raise DealflowError(f"stage #{i} must be a string or mapping, got {type(item).__name__}")
        sname = str(sname).strip()
        if not sname:
            raise DealflowError(f"stage #{i} has an empty name")
        if sname in seen_names:
            raise DealflowError(f"duplicate stage name: {sname!r}")
        seen_names.add(sname)
        st = Stage(name=sname, order=i, terminal=terminal, won=won)
        stages.append(st)
        if won:
            won_stage = st.name
            won_count += 1
        elif terminal:
            lost_stages.add(st.name)

    if won_count > 1:
        raise DealflowError(
            "pipeline defines more than one 'won' stage; exactly one is allowed"
        )

    if won_stage is None:
        # No stage was explicitly marked won: promote the last NON-terminal
        # stage to the won stage. Never silently turn a 'lost'/terminal stage
        # into the win condition (that inverts every forecast).
        candidates = [s for s in stages if not s.terminal]
        if not candidates:
            raise DealflowError(
                "pipeline has no open stages and no 'won' stage to advance toward"
            )
        winner = candidates[-1]
        winner.terminal = True
        winner.won = True
        won_stage = winner.name

    return Pipeline(name=name, stages=stages, won_stage=won_stage, lost_stages=lost_stages)


def load_pipeline(path: str) -> Pipeline:
    with open(path, "r", encoding="utf-8") as fh:
        return parse_pipeline(fh.read())


def _parse_date(s: str) -> _dt.date:
    s = (s or "").strip()
    if not s:
        raise DealflowError("empty date value")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise DealflowError(f"unrecognized date: {s!r}")


def load_deals(path_or_text: str, *, is_text: bool = False) -> list[Deal]:
    """Load deals from a CSV event log.

    Expected columns (case-insensitive): deal_id, stage, date, amount
    One row per stage-entry event. Amount may repeat per deal; the max seen is
    used. Returns a list of Deal with chronologically-sorted histories.
    """
    if is_text:
        fh = io.StringIO(path_or_text)
    else:
        fh = open(path_or_text, "r", encoding="utf-8", newline="")
    try:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise DealflowError("deals CSV is empty")
        cols = {c.lower().strip(): c for c in reader.fieldnames}
        required = ["deal_id", "stage", "date"]
        for r in required:
            if r not in cols:
                raise DealflowError(f"deals CSV missing required column: {r!r}")
        has_amount = "amount" in cols

        events: dict[str, list[tuple[str, _dt.date]]] = {}
        amounts: dict[str, float] = {}
        for lineno, row in enumerate(reader, start=2):  # header is line 1
            did = (row[cols["deal_id"]] or "").strip()
            if not did:
                continue
            stage = (row[cols["stage"]] or "").strip()
            if not stage:
                raise DealflowError(
                    f"row {lineno}: deal {did!r} has an empty stage"
                )
            try:
                date = _parse_date(row[cols["date"]])
            except DealflowError as e:
                raise DealflowError(f"row {lineno} (deal {did!r}): {e}") from None
            events.setdefault(did, []).append((stage, date))
            if has_amount:
                raw = (row[cols["amount"]] or "").strip().replace("$", "").replace(",", "")
                if raw:
                    try:
                        amt = float(raw)
                    except ValueError:
                        raise DealflowError(
                            f"row {lineno} (deal {did!r}): amount {raw!r} is not a number"
                        ) from None
                    if amt < 0:
                        raise DealflowError(
                            f"row {lineno} (deal {did!r}): amount {amt} is negative"
                        )
                    amounts[did] = max(amounts.get(did, 0.0), amt)
    finally:
        if not is_text:
            fh.close()

    deals = []
    for did, hist in events.items():
        hist.sort(key=lambda x: x[1])
        deals.append(Deal(deal_id=did, amount=amounts.get(did, 0.0), history=hist))
    deals.sort(key=lambda d: d.deal_id)
    return deals


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def analyze(pipeline: Pipeline, deals: list[Deal]) -> Report:
    open_stage_names = [s.name for s in pipeline.open_stages]
    won = pipeline.won_stage

    # entered[stage]   = # deals that ever entered stage
    # advanced[stage]  = # deals that entered stage AND later reached a later stage
    # durations[stage] = list of days spent in stage (only when deal left it)
    entered: dict[str, int] = {s.name: 0 for s in pipeline.stages}
    advanced: dict[str, int] = {s.name: 0 for s in pipeline.stages}
    durations: dict[str, list[float]] = {s.name: [] for s in pipeline.stages}

    won_count = lost_count = 0
    won_value = open_value = 0.0

    for d in deals:
        seen_stages = set()
        for i, (stage, date) in enumerate(d.history):
            if stage not in entered:
                raise DealflowError(
                    f"deal {d.deal_id!r} references unknown stage {stage!r}"
                )
            if stage not in seen_stages:
                entered[stage] += 1
                seen_stages.add(stage)
            if i + 1 < len(d.history):
                nxt_stage, nxt_date = d.history[i + 1]
                durations[stage].append((nxt_date - date).days)
                # Advancing = moving strictly forward in pipeline order toward
                # the win condition. A transition INTO a lost/terminal-loss
                # stage is NOT an advance even though a lost stage may sit at a
                # higher order index — it is the opposite of progress, and
                # counting it inflates advance rates and P(win).
                if (
                    pipeline.index(nxt_stage) > pipeline.index(stage)
                    and nxt_stage not in pipeline.lost_stages
                ):
                    advanced[stage] += 1

        cur = d.current_stage
        if cur == won:
            won_count += 1
            won_value += d.amount
        elif cur in pipeline.lost_stages:
            lost_count += 1
        else:
            open_value += d.amount

    # Advance rate per open stage = advanced / entered (smoothed at 0 if none).
    advance_rate: dict[str, float] = {}
    for name in open_stage_names:
        e = entered[name]
        advance_rate[name] = (advanced[name] / e) if e else 0.0

    # P(win | stage) = product of advance rates from this stage to the won stage.
    # Build using the ordered open stages.
    p_win: dict[str, float] = {}
    ordered_open = sorted(pipeline.open_stages, key=lambda s: s.order)
    for idx, st in enumerate(ordered_open):
        p = 1.0
        for downstream in ordered_open[idx:]:
            p *= advance_rate[downstream.name]
        p_win[st.name] = p
    p_win[won] = 1.0
    for ls in pipeline.lost_stages:
        p_win[ls] = 0.0

    # Weighted forecast over OPEN deals.
    weighted = 0.0
    deal_rows = []
    for d in deals:
        cur = d.current_stage
        pw = p_win.get(cur, 0.0)
        is_open = cur not in pipeline.lost_stages and cur != won
        ev = d.amount * pw if is_open else 0.0
        weighted += ev
        age_days = (d.history[-1][1] - d.history[0][1]).days
        deal_rows.append({
            "deal_id": d.deal_id,
            "current_stage": cur,
            "amount": round(d.amount, 2),
            "status": "won" if cur == won else ("lost" if cur in pipeline.lost_stages else "open"),
            "p_win": round(pw, 4),
            "expected_value": round(ev, 2),
            "age_days": age_days,
        })

    stage_rows = []
    for st in pipeline.stages:
        durs = durations[st.name]
        avg_days = round(sum(durs) / len(durs), 2) if durs else None
        stage_rows.append({
            "stage": st.name,
            "order": st.order,
            "terminal": st.terminal,
            "won": st.won,
            "entered": entered[st.name],
            "advanced": advanced[st.name],
            "advance_rate": round(advance_rate.get(st.name, 0.0), 4) if not st.terminal else None,
            "avg_days_in_stage": avg_days,
            "p_win": round(p_win.get(st.name, 0.0), 4),
        })

    total = len(deals)
    decided = won_count + lost_count
    win_rate = (won_count / decided) if decided else 0.0

    return Report(
        pipeline=pipeline.name,
        total_deals=total,
        open_deals=total - won_count - lost_count,
        won_deals=won_count,
        lost_deals=lost_count,
        open_value=open_value,
        won_value=won_value,
        weighted_forecast=weighted,
        overall_win_rate=win_rate,
        stages=stage_rows,
        deals=deal_rows,
    )
