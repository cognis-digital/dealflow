"""21 · Capital-source taxonomy — browse and extend the funding-vehicle catalog.

Audience: a capital advisor mapping the funding landscape.

Walks the built-in taxonomy (SBIR/STTR, OTA, APFIT, defense VC, strategic CVC,
In-Q-Tel-style, grants, project finance, venture debt), groups by category, and
then merges a user-supplied private fund over the seed — showing the catalog is
extensible, id-keyed, and override-safe.

Offline. Exit 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.capital_sources import default_catalog          # noqa: E402
from demos._common import money, rule                          # noqa: E402


def main() -> None:
    rule("21 · Capital-source taxonomy — the funding landscape, structured")

    cat = default_catalog()
    print(f"Seed catalog: {len(cat.sources)} funding-vehicle categories\n")

    for category in cat.categories():
        entries = cat.by_category(category)
        print(f"  {category}")
        for s in entries:
            lo, hi = s["check_min"], s["check_max"]
            dil = ", ".join(s.get("dilution") or [])
            print(f"    - {s['name']}")
            print(f"        check {money(lo)}–{money(hi)}  ·  {dil}  ·  "
                  f"~{s['timeline_months']}mo  ·  min TRL {s['min_trl']}")
            print(f"        {s['fit']}")
        print()

    rule("21b · Extend it — merge a private fund over the seed")
    my_fund = {
        "id": "greenway-defense-fund",
        "name": "Greenway Defense Fund",
        "category": "equity-vc",
        "check_min": 2_000_000,
        "check_max": 15_000_000,
        "dilution": ["equity"],
        "stages": ["series-a", "series-b"],
        "thesis": ["energy", "dual-use"],
        "dual_use": ["dual-use", "commercial"],
        "min_trl": 5,
        "fit": "Energy-transition dual-use equity.",
    }
    merged = cat.merge([my_fund])
    print(f"After merge: {len(merged.sources)} categories "
          f"(+1 private fund, seed preserved).")
    print(f"  new entry queryable by id: {merged.get('greenway-defense-fund')['name']}")
    print(f"  equity-vc category now holds "
          f"{len(merged.by_category('equity-vc'))} vehicles.")


if __name__ == "__main__":
    main()
