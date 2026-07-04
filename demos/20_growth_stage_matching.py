"""20 · Stage-aware matching — the same engine, a later-stage company.

Audience: a growth-stage operator raising a large equity round.

Contrast with demo 19: a Series B, revenue-generating company with an 8-figure
ask and an equity preference ranks *completely differently* — non-dilutive
micro-grants fall away, growth equity and strategic capital rise. Demonstrates
that the fit model is genuinely driven by the profile, not hardcoded.

Offline. Exit 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.capital_sources import default_catalog          # noqa: E402
from dealflow.matching import rank_matches                    # noqa: E402
from demos._common import money, rule                          # noqa: E402


def main() -> None:
    rule("20 · Stage-aware matching — a Series B scale-up")

    company = {
        "name": "Meridian Autonomy",
        "stage": "series-b",
        "ask": 25_000_000,
        "sectors": ["dual-use", "autonomy", "robotics"],
        "geography": ["us"],
        "dilution_pref": "equity",
        "dual_use": "dual-use",
        "trl": 8,
        "keywords": ["scale", "revenue", "expansion"],
    }
    print(f"Company: {company['name']}  ·  stage {company['stage']}  ·  "
          f"seeking {money(company['ask'])} (prefers {company['dilution_pref']})")

    sources = default_catalog().sources
    matches = rank_matches(company, sources)

    print("\nRanked fit across the full taxonomy:")
    print(f"  {'SOURCE':<36}{'FIT':>5}  BAND")
    print("  " + "-" * 54)
    for m in matches:
        print(f"  {m.source[:35]:<36}{m.score:>4.0f}  {m.band}")

    top = {m.source for m in matches[:3]}
    print("\nNote how the ranking inverted vs. an early-stage profile:")
    print(f"  - Best fits now: {', '.join(sorted(top))}")
    micro = next(m for m in matches if "Phase I" in m.source)
    print(f"  - Early micro-grant (SBIR Phase I) fell to {micro.score:.0f}/100 "
          f"({micro.band}) — check size and stage no longer align.")


if __name__ == "__main__":
    main()
