"""Scenario 7 - Pure conversion analysis with no dollar amounts.

Not every pipeline tracks deal size. A community/free-tier funnel may only care
about conversion and velocity. dealflow works fine with an amount-less deal log:
the dollar forecast is $0, but every conversion and velocity number is still
computed. This runs the 07-minimal-noamount sample.
"""
from _common import by_stage, load, rule


def main() -> None:
    pipeline, rep = load("07-minimal-noamount")
    rule("CONVERSION-ONLY FUNNEL  -  no amounts, still real math")

    print(f"\nPipeline: {rep.pipeline}   ({rep.total_deals} deals)\n")
    print(f"Open pipeline value : ${rep.open_value:,.0f}  (no amount column -> zero)")
    print(f"Weighted forecast   : ${rep.weighted_forecast:,.0f}")

    by = by_stage(rep)
    open_stages = [s["stage"] for s in rep.stages if not s["terminal"]]
    print("\nConversion still computes without a single dollar figure:")
    print("  STAGE           ENTERED   ADVANCE%   AVG_DAYS")
    print("  " + "-" * 46)
    for name in open_stages:
        s = by[name]
        rate = f"{s['advance_rate'] * 100:.0f}%"
        days = "-" if s["avg_days_in_stage"] is None else f"{s['avg_days_in_stage']:.1f}"
        print(f"  {name:<16}{s['entered']:>7}{rate:>11}{days:>11}")

    print("\nTakeaway: forecasting in dollars is optional; the state-machine")
    print("conversion analysis is the load-bearing part and needs no amounts.")


if __name__ == "__main__":
    main()
