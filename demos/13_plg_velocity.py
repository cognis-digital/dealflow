"""Scenario 13 - Product-led-growth velocity in days, not months.

Self-serve funnels move fast: signup to paid can be under a week. dealflow's
velocity metric works at that timescale and the advance rates tell you where
even a fast funnel leaks. This runs the 13-fast-velocity sample.
"""
from _common import by_stage, load, rule


def main() -> None:
    pipeline, rep = load("13-fast-velocity")
    rule("PLG VELOCITY  -  a funnel measured in days")

    by = by_stage(rep)
    open_stages = [s["stage"] for s in rep.stages if not s["terminal"]]

    print(f"\nPipeline: {rep.pipeline}   ({rep.total_deals} users through the funnel)\n")
    print("  STAGE          ENTERED   ADVANCE%   AVG_DAYS")
    print("  " + "-" * 45)
    for name in open_stages:
        s = by[name]
        rate = f"{s['advance_rate'] * 100:.0f}%"
        days = "-" if s["avg_days_in_stage"] is None else f"{s['avg_days_in_stage']:.1f}"
        print(f"  {name:<15}{s['entered']:>6}{rate:>11}{days:>11}")

    timed = [by[n] for n in open_stages if by[n]["avg_days_in_stage"] is not None]
    if timed:
        fastest = min(timed, key=lambda s: s["avg_days_in_stage"])
        print(f"\nFastest stage: '{fastest['stage']}' at "
              f"{fastest['avg_days_in_stage']:.1f} days average.")
    print(f"Decided win (paid) rate: {rep.overall_win_rate * 100:.0f}%.")
    print("For PLG, watch conversion % and days-in-stage; the dollar forecast")
    print("is secondary because individual ACVs are tiny.")


if __name__ == "__main__":
    main()
