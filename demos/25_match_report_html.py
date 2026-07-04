"""25 · Reports — self-contained HTML match report + teaming brief.

Audience: anyone who needs a shareable artifact for a data room or an email.

Generates a full capital-match report and a teaming brief as single-file HTML
with inline CSS, NO JavaScript and NO external/CDN assets — they open offline,
air-gapped, and paste cleanly into an email. Also emits the machine-readable
CSV/JSON alongside. Writes into a temp dir and verifies self-containment.

Offline. Exit 0.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dealflow.capital_sources import default_catalog                     # noqa: E402
from dealflow.matching import rank_matches                               # noqa: E402
from dealflow.teaming import Opportunity, TeamingGraph, recommend_team   # noqa: E402
from dealflow.reports import (                                           # noqa: E402
    match_report_html,
    matches_csv,
    teaming_brief_html,
)
from demos._common import rule                                           # noqa: E402


def _assert_self_contained(name: str, html_text: str) -> None:
    problems = []
    if "<script" in html_text.lower():
        problems.append("contains <script>")
    if "http://" in html_text or "https://" in html_text:
        problems.append("references an external URL")
    if "src=" in html_text:
        problems.append("has an external src=")
    verdict = "OK — self-contained" if not problems else "PROBLEM: " + ", ".join(problems)
    print(f"  {name}: {verdict} ({len(html_text):,} bytes)")


def main() -> None:
    rule("25 · Reports — offline HTML artifacts (no JS, no CDN)")

    company = {
        "name": "Aperture Sensing", "stage": "seed", "ask": 1_500_000,
        "sectors": ["dual-use", "deep-tech", "sensors"], "dual_use": "dual-use", "trl": 4,
    }
    matches = rank_matches(company, default_catalog().sources, top=5)

    opp = Opportunity.from_dict({
        "name": "Counter-UAS Sensing Program",
        "required": ["radar", "edge-ai", "systems-integration", "cybersecurity"],
        "set_aside_goals": ["sdvosb", "8(a)"],
    })
    roster = [
        {"id": "primeco", "name": "PrimeCo Systems", "role": "prime",
         "capabilities": ["systems-integration", "radar"]},
        {"id": "edgeai", "name": "EdgeAI Labs", "capabilities": ["edge-ai"], "set_asides": ["sdvosb"]},
        {"id": "cybersb", "name": "CyberShield SB", "capabilities": ["cybersecurity"], "set_asides": ["8(a)"]},
    ]
    graph = TeamingGraph.from_dicts(roster)
    rec = recommend_team(graph, opp)

    outdir = tempfile.mkdtemp(prefix="dealflow-report-")
    match_html = match_report_html(company["name"], matches)
    team_html = teaming_brief_html(rec, opp, {o.id: o for o in graph.orgs})

    match_path = os.path.join(outdir, "match_report.html")
    team_path = os.path.join(outdir, "teaming_brief.html")
    csv_path = os.path.join(outdir, "matches.csv")
    with open(match_path, "w", encoding="utf-8") as fh:
        fh.write(match_html)
    with open(team_path, "w", encoding="utf-8") as fh:
        fh.write(team_html)
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write(matches_csv(matches))

    print(f"Wrote artifacts to {outdir}\n")
    print("Self-containment check:")
    _assert_self_contained("match_report.html", match_html)
    _assert_self_contained("teaming_brief.html", team_html)

    print("\nAlso exported machine-readable matches.csv:")
    print("  " + matches_csv(matches).splitlines()[0])
    print("  " + matches_csv(matches).splitlines()[1])

    print("\nThese HTML files render in any browser, offline — drop them straight")
    print("into a data room or attach to an email. No network required.")


if __name__ == "__main__":
    main()
