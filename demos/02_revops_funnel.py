"""Scenario 2 - RevOps / sales operations.

RevOps owns the funnel mechanics: where do deals leak, and where do they sit?
dealflow computes two things per stage straight from the event log — the
advance rate (what fraction of deals that entered ever moved forward) and the
velocity (average days a deal spends in the stage before leaving it). Together
they pinpoint the leak and the bottleneck.

Here we use a SaaS funnel whose procurement/legal stage is a known stall point.
"""
from _common import by_stage, load, rule


def main() -> None:
    pipeline, rep = load("02-saas-monthly")
    rule("REVOPS FUNNEL ANALYSIS  -  find the leak and the bottleneck")

    by = by_stage(rep)
    open_stages = [s["stage"] for s in rep.stages if not s["terminal"]]

    print(f"\nPipeline: {rep.pipeline}  ({rep.total_deals} deals through the funnel)\n")
    print("  STAGE             ENTERED   ADVANCED   ADVANCE%   AVG_DAYS")
    print("  " + "-" * 58)
    for name in open_stages:
        s = by[name]
        adv = f"{s['advance_rate'] * 100:.0f}%"
        days = "-" if s["avg_days_in_stage"] is None else f"{s['avg_days_in_stage']:.1f}"
        print(f"  {name:<16}{s['entered']:>8}{s['advanced']:>11}{adv:>11}{days:>11}")

    # Biggest leak = lowest advance rate among stages with entries.
    leaky = min(
        (s for s in (by[n] for n in open_stages) if s["entered"] > 0),
        key=lambda s: s["advance_rate"],
    )
    # Slowest = highest avg days in stage.
    timed = [by[n] for n in open_stages if by[n]["avg_days_in_stage"] is not None]
    slow = max(timed, key=lambda s: s["avg_days_in_stage"]) if timed else None

    print("\nDiagnosis:")
    print(f"  Biggest leak     : '{leaky['stage']}' — only "
          f"{leaky['advance_rate'] * 100:.0f}% of deals advance "
          f"({leaky['entered'] - leaky['advanced']} of {leaky['entered']} drop or stall here).")
    if slow:
        print(f"  Biggest bottleneck: '{slow['stage']}' — deals sit "
              f"{slow['avg_days_in_stage']:.1f} days on average before moving.")
    print("\nAction: fix the stage with the worst advance rate first; it caps")
    print("the whole funnel's throughput regardless of how much you pour in at top.")


if __name__ == "__main__":
    main()
