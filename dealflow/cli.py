"""Command-line interface for DEALFLOW.

Examples
--------
  # Forecast a pipeline from a CSV deal log
  dealflow forecast --pipeline pipeline.yml --deals deals.csv

  # Machine-readable output for CI / piping
  dealflow forecast -p pipeline.yml -d deals.csv --format json | jq .weighted_forecast

  # Fail CI when the weighted forecast falls below target (gate)
  dealflow forecast -p pipeline.yml -d deals.csv --min-forecast 100000

  # Capital matchmaking + strategic teaming engine
  dealflow match   -c company.yml -s sources.yml      # ranked, explainable fit
  dealflow sources --category equity-vc               # capital-source taxonomy
  dealflow team    -o opportunity.yml -r roster.yml   # recommend a team + gaps
  dealflow pipeline -f pipeline.yml                   # opportunity tracker
  dealflow report  match -c company.yml -s sources.yml -o out.html

Exit codes
----------
  0  success and any gate passed
  1  gate failed (forecast below --min-forecast, or win-rate below --min-win-rate)
  2  usage / parse / data error
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys

from . import TOOL_NAME, TOOL_VERSION
from .core import load_pipeline, load_deals, analyze, DealflowError, Report, _yaml_load


def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def _render_table(rep: Report) -> str:
    lines = []
    lines.append(f"Pipeline: {rep.pipeline}")
    lines.append(
        f"Deals: {rep.total_deals} total | {rep.open_deals} open | "
        f"{rep.won_deals} won | {rep.lost_deals} lost"
    )
    lines.append(f"Win rate (decided): {rep.overall_win_rate * 100:.1f}%")
    lines.append("")
    lines.append("Stage breakdown:")
    hdr = f"  {'STAGE':<16}{'ENTER':>6}{'ADV':>5}{'ADV%':>7}{'AVG_DAYS':>10}{'P(WIN)':>9}"
    lines.append(hdr)
    lines.append("  " + "-" * (len(hdr) - 2))
    for s in rep.stages:
        adv = "" if s["advance_rate"] is None else f"{s['advance_rate'] * 100:.0f}%"
        avg = "" if s["avg_days_in_stage"] is None else f"{s['avg_days_in_stage']:.1f}"
        lines.append(
            f"  {s['stage']:<16}{s['entered']:>6}{s['advanced']:>5}{adv:>7}"
            f"{avg:>10}{s['p_win'] * 100:>8.0f}%"
        )
    lines.append("")
    lines.append("Forecast:")
    lines.append(f"  Open pipeline value : {_fmt_money(rep.open_value)}")
    lines.append(f"  Won value (closed)  : {_fmt_money(rep.won_value)}")
    lines.append(f"  Weighted forecast   : {_fmt_money(rep.weighted_forecast)}")
    return "\n".join(lines)


def _render_csv(rep: Report) -> str:
    """Emit the per-deal forecast as CSV — pipe straight into a spreadsheet,
    BI tool, or CRM bulk-import. One row per deal, header included.
    """
    cols = [
        "deal_id", "current_stage", "status",
        "amount", "p_win", "expected_value", "age_days",
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for d in rep.deals:
        w.writerow({k: d[k] for k in cols})
    return buf.getvalue().rstrip("\n")


def _load_profile(path: str) -> object:
    """Load a YAML/JSON profile file into a Python object (dict/list)."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    stripped = text.lstrip()
    if stripped[:1] in "[{":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return _yaml_load(text)


def _parse_weights(spec: str | None) -> dict | None:
    """Parse ``--weights name=1.5,other=0.5`` into a dict."""
    if not spec:
        return None
    out: dict[str, float] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        k, _, v = part.partition("=")
        try:
            out[k.strip()] = float(v)
        except ValueError:
            raise DealflowError(f"bad weight spec: {part!r} (want name=number)") from None
    return out


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Model a sales pipeline as a YAML state machine and compute "
            "conversion, velocity, and a weighted forecast from a CSV deal log. "
            "Pipeline-as-code: a reproducible forecast artifact for CI."
        ),
        epilog=(
            "example:\n"
            "  dealflow forecast -p pipeline.yml -d deals.csv\n"
            "  dealflow forecast -p pipeline.yml -d deals.csv --format json --min-forecast 100000\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    fc = sub.add_parser(
        "forecast",
        help="compute conversion/velocity/forecast from a pipeline + deal log",
        description="Compute stage conversion rates, velocity, and a weighted forecast.",
    )
    fc.add_argument("-p", "--pipeline", required=True, help="path to pipeline YAML file")
    fc.add_argument("-d", "--deals", required=True, help="path to deals CSV event log")
    fc.add_argument(
        "--format", choices=("table", "json", "csv"), default="table",
        help="output format: table (human), json (full report), "
             "csv (per-deal rows for spreadsheets/CRM import) (default: table)",
    )
    fc.add_argument(
        "--min-forecast", type=float, default=None,
        help="exit non-zero if weighted forecast is below this value (CI gate)",
    )
    fc.add_argument(
        "--min-win-rate", type=float, default=None,
        help="exit non-zero if win rate (0-1) is below this value (CI gate)",
    )

    # --- match: explainable capital-source fit scoring ---------------------- #
    mt = sub.add_parser(
        "match",
        help="score a company/tech profile against capital sources (explainable)",
        description="Rank capital sources by transparent, weighted fit factors.",
    )
    mt.add_argument("-c", "--company", required=True, help="company/technology profile (YAML/JSON)")
    mt.add_argument(
        "-s", "--sources", default=None,
        help="capital-source catalog (YAML/JSON); default: built-in seed taxonomy",
    )
    mt.add_argument("--format", choices=("table", "json", "csv"), default="table")
    mt.add_argument("--top", type=int, default=None, help="show only the top N matches")
    mt.add_argument("--min-score", type=float, default=0.0, help="drop matches below this 0-100 score")
    mt.add_argument("--weights", default=None, help="override factor weights, e.g. sector=2,stage=1")
    mt.add_argument("--explain", action="store_true", help="print full factor breakdown per match")

    # --- sources: browse the capital-source taxonomy ------------------------ #
    sc = sub.add_parser(
        "sources",
        help="list/inspect the capital-source funding taxonomy",
        description="The built-in (or merged) catalog of funding vehicles.",
    )
    sc.add_argument("-s", "--sources", default=None, help="user catalog to merge over the seed")
    sc.add_argument("--category", default=None, help="filter to a single category")
    sc.add_argument("--id", dest="source_id", default=None, help="show one source by id")
    sc.add_argument("--format", choices=("table", "json"), default="table")

    # --- team: recommend a teaming arrangement + gap analysis --------------- #
    tm = sub.add_parser(
        "team",
        help="recommend a teaming arrangement for an opportunity + gap analysis",
        description="Assemble a complementary team covering an opportunity's requirements.",
    )
    tm.add_argument("-o", "--opportunity", required=True, help="opportunity profile (YAML/JSON)")
    tm.add_argument("-r", "--roster", required=True, help="org roster (YAML/JSON list)")
    tm.add_argument("--prime", default=None, help="force a specific org id as the prime")
    tm.add_argument("--max-members", type=int, default=6, help="cap the team size (default 6)")
    tm.add_argument("--format", choices=("table", "json"), default="table")
    tm.add_argument(
        "--require-complete", action="store_true",
        help="exit non-zero if the recommended team leaves gaps (CI gate)",
    )

    # --- pipeline: opportunity/capture pipeline tracker --------------------- #
    pl = sub.add_parser(
        "pipeline",
        help="track a capture pipeline: weighted value + next-action prompts",
        description="Probability-weighted opportunity pipeline with next actions.",
    )
    pl.add_argument("-f", "--file", required=True, help="opportunity pipeline (YAML/JSON)")
    pl.add_argument("--format", choices=("table", "json"), default="table")
    pl.add_argument("--open-only", action="store_true", help="show only open opportunities")
    pl.add_argument(
        "--min-weighted", type=float, default=None,
        help="exit non-zero if the weighted pipeline is below this value (CI gate)",
    )

    # --- report: self-contained HTML artifacts ------------------------------ #
    rp = sub.add_parser(
        "report",
        help="render a self-contained HTML match report or teaming brief",
        description="Offline HTML artifacts (no JS/CDN) + CSV/JSON export.",
    )
    rp_sub = rp.add_subparsers(dest="report_kind", metavar="<kind>")
    rmt = rp_sub.add_parser("match", help="ranked capital-match report (HTML)")
    rmt.add_argument("-c", "--company", required=True)
    rmt.add_argument("-s", "--sources", default=None)
    rmt.add_argument("--top", type=int, default=None)
    rmt.add_argument("--weights", default=None)
    rmt.add_argument("-o", "--out", default=None, help="output file (default: stdout)")
    rmt.add_argument("--format", choices=("html", "csv", "json"), default="html")
    rtm = rp_sub.add_parser("team", help="teaming brief (HTML)")
    rtm.add_argument("-o", "--opportunity", required=True, dest="opportunity")
    rtm.add_argument("-r", "--roster", required=True)
    rtm.add_argument("--prime", default=None)
    rtm.add_argument("--max-members", type=int, default=6)
    rtm.add_argument("--out", default=None, help="output file (default: stdout)")
    rtm.add_argument("--format", choices=("html", "json"), default="html")

    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 2

    if args.command == "forecast":
        try:
            pipeline = load_pipeline(args.pipeline)
            deals = load_deals(args.deals)
            rep = analyze(pipeline, deals)
        except DealflowError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

        if args.format == "json":
            print(json.dumps(rep.to_dict(), indent=2))
        elif args.format == "csv":
            print(_render_csv(rep))
        else:
            print(_render_table(rep))

        gate_failed = False
        if args.min_forecast is not None and rep.weighted_forecast < args.min_forecast:
            print(
                f"gate: weighted forecast {rep.weighted_forecast:.2f} "
                f"< min {args.min_forecast:.2f}",
                file=sys.stderr,
            )
            gate_failed = True
        if args.min_win_rate is not None and rep.overall_win_rate < args.min_win_rate:
            print(
                f"gate: win rate {rep.overall_win_rate:.4f} "
                f"< min {args.min_win_rate:.4f}",
                file=sys.stderr,
            )
            gate_failed = True
        return 1 if gate_failed else 0

    if args.command == "match":
        return _cmd_match(args)
    if args.command == "sources":
        return _cmd_sources(args)
    if args.command == "team":
        return _cmd_team(args)
    if args.command == "pipeline":
        return _cmd_pipeline(args)
    if args.command == "report":
        return _cmd_report(args, parser)

    parser.print_help()
    return 2


# --------------------------------------------------------------------------- #
# Matchmaking / teaming / pipeline command handlers
# --------------------------------------------------------------------------- #
def _cmd_match(args) -> int:
    from .matching import rank_matches, explain
    from .capital_sources import merged_catalog, default_catalog
    try:
        company = _load_profile(args.company)
        if not isinstance(company, dict):
            raise DealflowError("company profile must be a mapping")
        cat = merged_catalog(args.sources) if args.sources else default_catalog()
        weights = _parse_weights(args.weights)
        matches = rank_matches(
            company, cat.sources, weights=weights, top=args.top, min_score=args.min_score,
        )
    except DealflowError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        from .reports import matches_json
        print(matches_json(matches))
    elif args.format == "csv":
        from .reports import matches_csv
        print(matches_csv(matches))
    else:
        cname = str(company.get("name") or "company")
        print(f"Capital matches for: {cname}  ({len(matches)} source(s))")
        print(f"  {'SOURCE':<34}{'FIT':>5}  BAND")
        print("  " + "-" * 52)
        for m in matches:
            print(f"  {m.source[:33]:<34}{m.score:>4.0f}  {m.band}")
        if args.explain:
            print()
            for m in matches:
                print(explain(m))
                print()
    return 0


def _cmd_sources(args) -> int:
    from .capital_sources import merged_catalog, default_catalog
    try:
        cat = merged_catalog(args.sources) if args.sources else default_catalog()
        if args.source_id:
            one = cat.get(args.source_id)
            items = [one]
        elif args.category:
            items = cat.by_category(args.category)
        else:
            items = cat.sources
    except DealflowError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"count": len(items), "sources": items}, indent=2))
    else:
        print(f"Capital sources ({len(items)}):")
        print(f"  {'ID':<20}{'CATEGORY':<24}{'CHECK':>22}  DILUTION")
        print("  " + "-" * 78)
        for s in items:
            lo = s.get("check_min")
            hi = s.get("check_max")
            band = f"${lo:,.0f}-${hi:,.0f}" if lo is not None and hi is not None else "-"
            dil = ",".join(s.get("dilution") or []) or s.get("capital_type") or "-"
            print(f"  {str(s.get('id'))[:19]:<20}{str(s.get('category') or '')[:23]:<24}"
                  f"{band:>22}  {dil}")
    return 0


def _cmd_team(args) -> int:
    from .teaming import TeamingGraph, Opportunity, recommend_team
    try:
        opp_raw = _load_profile(args.opportunity)
        roster_raw = _load_profile(args.roster)
        if isinstance(roster_raw, dict):
            roster_raw = roster_raw.get("roster") or roster_raw.get("orgs") or []
        opp = Opportunity.from_dict(opp_raw)
        graph = TeamingGraph.from_dicts(roster_raw)
        rec = recommend_team(graph, opp, prime=args.prime, max_members=args.max_members)
    except DealflowError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(rec.to_dict(), indent=2))
    else:
        orgs = {o.id: o for o in graph.orgs}
        print(f"Teaming recommendation: {opp.name}")
        print(f"  Prime: {orgs[rec.prime].name if rec.prime in orgs else rec.prime}")
        print(f"  Team ({len(rec.members)}): " +
              ", ".join(orgs[m].name if m in orgs else m for m in rec.members))
        print(f"  Required coverage: {rec.coverage * 100:.0f}%")
        if rec.uncovered:
            print(f"  Uncovered requirements: {', '.join(sorted(rec.uncovered))}")
        else:
            print("  Uncovered requirements: none")
        if opp.set_aside_goals:
            met = ", ".join(sorted(rec.set_asides_met)) or "none"
            miss = ", ".join(sorted(rec.set_asides_missing)) or "none"
            print(f"  Set-asides met: {met}  | missing: {miss}")
        print("  Rationale:")
        for r in rec.rationale:
            print(f"    - {r}")

    if getattr(args, "require_complete", False):
        if rec.uncovered or rec.set_asides_missing:
            print("gate: recommended team leaves gaps", file=sys.stderr)
            return 1
    return 0


def _cmd_pipeline(args) -> int:
    from .opps import parse_tracker
    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            tracker = parse_tracker(fh.read())
        summary = tracker.summary()
    except DealflowError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    rows = summary["opportunities"]
    if args.open_only:
        rows = [r for r in rows if r["status"] == "open"]

    if args.format == "json":
        out = dict(summary)
        out["opportunities"] = rows
        print(json.dumps(out, indent=2))
    else:
        print("Opportunity pipeline")
        print(f"  {summary['total_opportunities']} total | {summary['open']} open | "
              f"{summary['won']} won | {summary['lost']} lost")
        print(f"  Open value        : {_fmt_money(summary['open_value'])}")
        print(f"  Weighted pipeline : {_fmt_money(summary['weighted_pipeline'])}")
        print()
        print(f"  {'OPPORTUNITY':<26}{'STAGE':<12}{'VALUE':>12}{'P':>6}{'WEIGHTED':>12}")
        print("  " + "-" * 68)
        for r in rows:
            flag = "*" if r["stale"] else " "
            print(f"{flag} {r['name'][:25]:<26}{r['stage']:<12}"
                  f"{_fmt_money(r['value']):>12}{r['probability']*100:>5.0f}%"
                  f"{_fmt_money(r['weighted_value']):>12}")
        print()
        print("  Next actions:")
        for r in rows:
            if r["status"] == "open":
                print(f"    - [{r['name']}] {r['next_action']}")

    if args.min_weighted is not None and summary["weighted_pipeline"] < args.min_weighted:
        print(f"gate: weighted pipeline {summary['weighted_pipeline']:.2f} "
              f"< min {args.min_weighted:.2f}", file=sys.stderr)
        return 1
    return 0


def _write_or_print(text: str, out: str | None) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


def _cmd_report(args, parser) -> int:
    if not getattr(args, "report_kind", None):
        parser.parse_args(["report", "--help"])
        return 2
    if args.report_kind == "match":
        from .matching import rank_matches
        from .capital_sources import merged_catalog, default_catalog
        from .reports import match_report_html, matches_csv, matches_json
        try:
            company = _load_profile(args.company)
            if not isinstance(company, dict):
                raise DealflowError("company profile must be a mapping")
            cat = merged_catalog(args.sources) if args.sources else default_catalog()
            matches = rank_matches(
                company, cat.sources, weights=_parse_weights(args.weights), top=args.top,
            )
        except DealflowError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        cname = str(company.get("name") or "company")
        if args.format == "csv":
            _write_or_print(matches_csv(matches), args.out)
        elif args.format == "json":
            _write_or_print(matches_json(matches), args.out)
        else:
            _write_or_print(match_report_html(cname, matches), args.out)
        return 0

    if args.report_kind == "team":
        from .teaming import TeamingGraph, Opportunity, recommend_team
        from .reports import teaming_brief_html, team_json
        try:
            opp_raw = _load_profile(args.opportunity)
            roster_raw = _load_profile(args.roster)
            if isinstance(roster_raw, dict):
                roster_raw = roster_raw.get("roster") or roster_raw.get("orgs") or []
            opp = Opportunity.from_dict(opp_raw)
            graph = TeamingGraph.from_dicts(roster_raw)
            rec = recommend_team(graph, opp, prime=args.prime, max_members=args.max_members)
        except DealflowError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        if args.format == "json":
            _write_or_print(team_json(rec), args.out)
        else:
            orgs = {o.id: o for o in graph.orgs}
            _write_or_print(teaming_brief_html(rec, opp, orgs), args.out)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
