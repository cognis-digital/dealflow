"""19 · Capital matchmaking — explainable fit scoring (founder / capital-raise).

Audience: a defense-tech founder deciding *which* funding vehicle to chase.

Shows the transparent matching model: a company profile scored against the
built-in capital-source taxonomy, ranked, with the factor breakdown that drives
each score. No black box — every number reconciles to named, weighted factors.

Runs fully offline against the built-in seed taxonomy. Exit 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.capital_sources import default_catalog          # noqa: E402
from dealflow.matching import explain, rank_matches           # noqa: E402
from demos._common import money, rule                          # noqa: E402


def main() -> None:
    rule("19 · Capital matchmaking — which vehicle fits this company?")

    company = {
        "name": "Aperture Sensing",
        "stage": "seed",
        "ask": 1_500_000,
        "sectors": ["dual-use", "deep-tech", "sensors"],
        "technology": ["edge-ai"],
        "geography": ["us"],
        "dilution_pref": "non-dilutive",
        "dual_use": "dual-use",
        "trl": 4,
        "keywords": ["prototype", "innovation", "r&d"],
    }
    print(f"Company: {company['name']}  ·  stage {company['stage']}  ·  "
          f"seeking {money(company['ask'])} (prefers {company['dilution_pref']})")

    matches = rank_matches(company, default_catalog().sources, top=5)
    print("\nTop capital sources by explainable fit:")
    print(f"  {'SOURCE':<36}{'FIT':>5}  BAND")
    print("  " + "-" * 54)
    for m in matches:
        print(f"  {m.source[:35]:<36}{m.score:>4.0f}  {m.band}")

    best = matches[0]
    print(f"\nWhy the top match ({best.source}) scores {best.score:.0f}/100:")
    print(explain(best))

    print("\nWhat's holding it back (live factors scoring < 50%):")
    gaps = best.gaps()
    if gaps:
        for f in gaps:
            print(f"  - {f.name}: {f.raw * 100:.0f}% — {f.reason}")
    else:
        print("  - none; this is a clean fit.")

    print("\nTakeaway: chase the non-dilutive prototype vehicles first — the")
    print("factor breakdown tells the founder exactly why, not just a score.")


if __name__ == "__main__":
    main()
