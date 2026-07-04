"""23 · Teaming gap analysis — what a thin bench can't cover.

Audience: a BD lead deciding whether to bid, team up, or walk.

Runs the same recommender against a *thin* roster that cannot cover the
opportunity, surfacing exactly which required capabilities and set-aside goals
remain open — the go/no-go signal — and then uses the complementary-edge graph
to show which single partner would close the most of the gap.

Offline. Exit 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.teaming import Opportunity, TeamingGraph, gap_analysis, recommend_team  # noqa: E402
from demos._common import rule                                                          # noqa: E402


def main() -> None:
    rule("23 · Teaming gap analysis — bid, team, or walk?")

    opp = Opportunity.from_dict({
        "name": "Integrated ISR Platform",
        "required": ["radar", "edge-ai", "systems-integration", "cybersecurity", "satcom"],
        "set_aside_goals": ["sdvosb", "hubzone"],
    })
    thin_roster = [
        {"id": "primeco", "name": "PrimeCo Systems", "role": "prime",
         "capabilities": ["systems-integration", "radar"]},
        {"id": "edgeai", "name": "EdgeAI Labs", "role": "small-business",
         "capabilities": ["edge-ai"], "set_asides": ["sdvosb"]},
    ]
    graph = TeamingGraph.from_dicts(thin_roster)

    rec = recommend_team(graph, opp)
    print(f"Opportunity: {opp.name}")
    print(f"Best team from current bench: "
          f"{', '.join(rec.members)}  ({rec.coverage * 100:.0f}% coverage)\n")

    print("GAP ANALYSIS")
    print(f"  Uncovered requirements : {', '.join(sorted(rec.uncovered)) or 'none'}")
    print(f"  Unmet set-aside goals  : {', '.join(sorted(rec.set_asides_missing)) or 'none'}")

    # What kind of partner would close the gap?
    print("\nTo close the gap, seek a partner bringing:")
    for cap in sorted(rec.uncovered):
        print(f"  - {cap}")
    for sa in sorted(rec.set_asides_missing):
        print(f"  - set-aside status: {sa}")

    print("\nDecision: this bench is insufficient — either team up for the missing")
    print("capabilities/set-asides above, or no-bid. The gap list is the shopping list.")

    # sanity: adding the right partner would complete it
    complete_roster = thin_roster + [
        {"id": "fullstack", "name": "FullStack Defense",
         "capabilities": ["cybersecurity", "satcom"], "set_asides": ["hubzone"]},
    ]
    g2 = TeamingGraph.from_dicts(complete_roster)
    rec2 = recommend_team(g2, opp)
    print(f"\n(With the right partner added, coverage -> {rec2.coverage * 100:.0f}%, "
          f"complete={not rec2.uncovered and not rec2.set_asides_missing}.)")


if __name__ == "__main__":
    main()
