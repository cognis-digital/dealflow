"""22 · Strategic teaming — assemble a compliant team + gap analysis.

Audience: a capture manager building a team for a target opportunity.

Given a target opportunity's required capabilities and set-aside goals, and a
roster of primes / subs / small businesses, the engine greedily assembles a
complementary team, reports required-capability coverage, and shows the
rationale for each addition.

Offline. Exit 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.teaming import Opportunity, TeamingGraph, recommend_team   # noqa: E402
from demos._common import rule                                            # noqa: E402


def main() -> None:
    rule("22 · Strategic teaming — cover the requirement, meet the set-asides")

    opp = Opportunity.from_dict({
        "name": "Counter-UAS Sensing Program",
        "required": ["radar", "edge-ai", "systems-integration", "cybersecurity"],
        "preferred": ["logistics"],
        "set_aside_goals": ["sdvosb", "8(a)"],
    })
    roster = [
        {"id": "primeco", "name": "PrimeCo Systems", "role": "prime",
         "capabilities": ["systems-integration", "radar", "program-management"],
         "past_performance": ["dod-c2"]},
        {"id": "edgeai", "name": "EdgeAI Labs", "role": "small-business",
         "capabilities": ["edge-ai", "ml-ops"], "set_asides": ["sdvosb"]},
        {"id": "cybersb", "name": "CyberShield SB", "role": "small-business",
         "capabilities": ["cybersecurity"], "set_asides": ["8(a)", "hubzone"]},
        {"id": "logico", "name": "LogiCo", "role": "sub",
         "capabilities": ["logistics", "supply-chain"]},
    ]
    graph = TeamingGraph.from_dicts(roster)
    orgs = {o.id: o for o in graph.orgs}

    print(f"Opportunity: {opp.name}")
    print(f"  required : {', '.join(sorted(opp.required_capabilities))}")
    print(f"  set-aside goals: {', '.join(sorted(opp.set_aside_goals))}\n")

    rec = recommend_team(graph, opp)
    print(f"Recommended team ({len(rec.members)}):")
    for oid in rec.members:
        o = orgs[oid]
        tag = "  [PRIME]" if oid == rec.prime else ""
        print(f"  - {o.name}{tag}: {', '.join(sorted(o.capabilities))}")

    print(f"\nRequired-capability coverage: {rec.coverage * 100:.0f}%")
    print(f"Set-asides met: {', '.join(sorted(rec.set_asides_met)) or 'none'}")
    print(f"Uncovered requirements: {', '.join(sorted(rec.uncovered)) or 'none'}")

    print("\nCapture rationale:")
    for r in rec.rationale:
        print(f"  - {r}")

    complete = not rec.uncovered and not rec.set_asides_missing
    print(f"\nVerdict: {'COMPLETE — team covers the requirement and set-aside goals.' if complete else 'GAPS REMAIN.'}")


if __name__ == "__main__":
    main()
