"""Scenario 16 - Clear errors on bad input.

Garbage in should produce a precise, actionable message — not a stack trace or,
worse, a silently wrong number. This demo feeds dealflow a series of malformed
inputs and shows the specific DealflowError each one raises: a malformed
pipeline, a deal referencing an unknown stage, a bad date, and a negative
amount.
"""
from _common import rule
from dealflow.core import (
    DealflowError,
    analyze,
    load_deals,
    load_pipeline,
    parse_pipeline,
)
from _common import sample


CASES = [
    (
        "pipeline with no stages",
        lambda: parse_pipeline("name: Broken\nstages:\n"),
    ),
    (
        "pipeline with a duplicate stage name",
        lambda: parse_pipeline("name: X\nstages:\n  - lead\n  - lead\n"),
    ),
    (
        "pipeline with two 'won' stages",
        lambda: parse_pipeline(
            "name: X\nstages:\n  - {name: a, type: won}\n  - {name: b, type: won}\n"
        ),
    ),
    (
        "deal referencing an unknown stage",
        lambda: analyze(
            load_pipeline(sample("01-basic")[0]),
            load_deals("deal_id,stage,date,amount\nZ,ghost,2026-01-01,10\n", is_text=True),
        ),
    ),
    (
        "deal log with an unparseable date",
        lambda: load_deals(
            "deal_id,stage,date\nZ,lead,not-a-date\n", is_text=True
        ),
    ),
    (
        "deal log with a negative amount",
        lambda: load_deals(
            "deal_id,stage,date,amount\nZ,lead,2026-01-01,-500\n", is_text=True
        ),
    ),
    (
        "deal CSV missing a required column",
        lambda: load_deals("deal_id,stage\nZ,lead\n", is_text=True),
    ),
]


def main() -> None:
    rule("ERROR HANDLING  -  precise messages, never a silent wrong answer")
    print()
    for label, fn in CASES:
        try:
            fn()
        except DealflowError as e:
            print(f"  {label:<42} -> DealflowError: {e}")
        else:  # pragma: no cover - would indicate a hardening regression
            raise AssertionError(f"expected {label!r} to raise DealflowError")
    print("\nEvery malformed input produced a specific, typed error. Callers can")
    print("catch DealflowError and surface the message to a user or CI log.")


if __name__ == "__main__":
    main()
