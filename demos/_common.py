"""Shared helpers for the demo scenarios.

Every scenario loads a bundled sample pipeline (YAML state machine) and deal
event log (CSV) from this repo's `demos/NN-*/` directories and drives the REAL
dealflow API — `parse_pipeline` / `load_deals` / `analyze` from
`dealflow.core`. No network, no fabricated numbers: the output you see is what
the engine computes, fully offline.
"""
from __future__ import annotations

import os
import sys

# allow `python demos/xx.py` from anywhere
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.core import (        # noqa: E402
    Pipeline,
    Report,
    analyze,
    load_deals,
    load_pipeline,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS_DIR = os.path.join(REPO_ROOT, "demos")


def sample(name: str) -> tuple[str, str]:
    """Return (pipeline.yml, deals.csv) paths for a bundled demo directory."""
    base = os.path.join(DEMOS_DIR, name)
    return os.path.join(base, "pipeline.yml"), os.path.join(base, "deals.csv")


def load(name: str) -> tuple[Pipeline, Report]:
    """Load a bundled sample by directory name and run the real analysis."""
    pipe_path, deals_path = sample(name)
    pipeline = load_pipeline(pipe_path)
    deals = load_deals(deals_path)
    return pipeline, analyze(pipeline, deals)


def rule(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def money(x: float) -> str:
    return f"${x:,.0f}"


def by_stage(report: Report) -> dict[str, dict]:
    return {s["stage"]: s for s in report.stages}
