"""26 · Teaming graph — complementary-capability edges across the roster.

Audience: a partnering lead exploring who complements whom, opportunity-agnostic.

The teaming graph's adjacency is computed from *complementary capabilities*:
an edge (A, B) exists when each brings capabilities the other lacks. This demo
lists the strongest complementary pairings in a roster and, for one anchor org,
ranks the partners that add the most new capability.

Offline. Exit 0.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.teaming import TeamingGraph                      # noqa: E402
from demos._common import rule                                 # noqa: E402


def main() -> None:
    rule("26 · Teaming graph — strongest complementary pairings")

    roster = [
        {"id": "primeco", "name": "PrimeCo", "capabilities": ["systems-integration", "radar"]},
        {"id": "edgeai", "name": "EdgeAI", "capabilities": ["edge-ai", "ml-ops"]},
        {"id": "cybersb", "name": "CyberSB", "capabilities": ["cybersecurity", "systems-integration"]},
        {"id": "satco", "name": "SatCo", "capabilities": ["satcom", "rf-engineering"]},
        {"id": "logico", "name": "LogiCo", "capabilities": ["logistics"]},
    ]
    graph = TeamingGraph.from_dicts(roster)
    names = {o.id: o.name for o in graph.orgs}

    print(f"Roster: {len(graph.orgs)} organizations\n")
    print("Top complementary pairings (each partner covers the other's gaps):")
    for e in graph.edges()[:5]:
        print(f"  {names[e['a']]} + {names[e['b']]}  "
              f"(complementarity {e['complementarity']})")
        print(f"      {names[e['a']]} adds: {', '.join(e['a_adds']) or '—'}")
        print(f"      {names[e['b']]} adds: {', '.join(e['b_adds']) or '—'}")

    anchor = "primeco"
    print(f"\nBest partners for {names[anchor]} (most NEW capability first):")
    for org, new in graph.complements(anchor)[:4]:
        print(f"  - {org.name}: brings {', '.join(sorted(new))}")

    print("\nUse this to find teaming partners before an opportunity even lands.")


if __name__ == "__main__":
    main()
