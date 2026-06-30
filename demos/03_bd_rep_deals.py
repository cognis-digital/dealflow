"""Scenario 3 - BD reps / account executives.

A rep doesn't care about the funnel in aggregate — they care about THEIR open
deals: which to push this week, and which are quietly rotting. dealflow gives
every open deal a P(win) from its current stage and an expected value, plus the
age in days so stalled deals surface themselves.

This uses an enterprise field-sales pipeline with long cycles.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("03-enterprise-longcycle")
    rule("BD REP WORKLIST  -  what to push, what's rotting")

    open_deals = [d for d in rep.deals if d["status"] == "open"]
    # Highest expected value first = best use of a rep's limited hours.
    open_deals.sort(key=lambda d: d["expected_value"], reverse=True)

    print(f"\nPipeline: {rep.pipeline}   |   your open deals: {len(open_deals)}\n")
    print("  DEAL          STAGE             AMOUNT     P(WIN)   EXP_VALUE   AGE")
    print("  " + "-" * 66)
    for d in open_deals:
        print(f"  {d['deal_id']:<13}{d['current_stage']:<16}"
              f"{money(d['amount']):>10}{d['p_win'] * 100:>8.0f}%"
              f"{money(d['expected_value']):>12}{d['age_days']:>6}")

    print("\nFocus (highest expected value — most forecast dollars per hour spent):")
    for d in open_deals[:3]:
        print(f"  - {d['deal_id']} in '{d['current_stage']}': "
              f"{money(d['expected_value'])} expected ({d['p_win'] * 100:.0f}% to close).")

    # Stalled = oldest open deals.
    aging = sorted(open_deals, key=lambda d: d["age_days"], reverse=True)[:2]
    print("\nRotting (oldest open deals — chase or disqualify):")
    for d in aging:
        print(f"  - {d['deal_id']} has been open {d['age_days']} days, "
              f"now in '{d['current_stage']}'.")


if __name__ == "__main__":
    main()
