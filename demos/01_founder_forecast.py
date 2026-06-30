"""Scenario 1 - Founders & sales leaders.

The board asks one question: "What's the number?" A founder shouldn't have to
massage a spreadsheet to answer it. Point dealflow at a committed pipeline YAML
and a CRM export, and the weighted forecast — every open deal discounted by its
historical probability of closing — falls out as a reproducible artifact.

This plays the founder's side of that conversation against the real engine.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("01-basic")
    rule("FOUNDER / SALES-LEADER FORECAST  -  what's the number, really?")

    print(f"\nPipeline (committed YAML state machine): {rep.pipeline}")
    print(
        f"Deals on file: {rep.total_deals} "
        f"({rep.open_deals} open, {rep.won_deals} won, {rep.lost_deals} lost)"
    )

    print("\nThe two numbers a board deck conflates — and dealflow separates:")
    print(f"  Open pipeline value (raw, optimistic) : {money(rep.open_value)}")
    print(f"  Weighted forecast (risk-adjusted)      : {money(rep.weighted_forecast)}")
    haircut = rep.open_value - rep.weighted_forecast
    pct = (haircut / rep.open_value * 100) if rep.open_value else 0.0
    print(f"  --> the engine discounts {money(haircut)} ({pct:.0f}%) "
          f"of raw pipeline as unlikely to close.")

    print(f"\nProven win rate on decided deals: {rep.overall_win_rate * 100:.1f}%")
    print("  (won / [won + lost] — the rate every forecast is implicitly betting on)")

    print("\nWhy a founder trusts this number:")
    print("  - it comes from a file in git, not a hand-edited slide")
    print("  - the discount per stage is the team's OWN historical advance rate")
    print("  - re-run on next month's export and the delta is the real movement")


if __name__ == "__main__":
    main()
