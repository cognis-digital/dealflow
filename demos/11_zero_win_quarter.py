"""Scenario 11 - The honest zero: a quarter with no wins.

A forecasting tool earns trust by refusing to invent value. When no deal has
ever reached the won stage, the historical advance rate into 'won' is zero, so
every open deal's P(win) is zero and the weighted forecast is $0 — not a
divide-by-zero, not an optimistic guess. This runs the 14-all-lost sample.
"""
from _common import by_stage, load, money, rule


def main() -> None:
    pipeline, rep = load("14-all-lost")
    rule("ZERO-WIN QUARTER  -  the forecast that honestly says $0")

    print(f"\nPipeline: {rep.pipeline}   "
          f"({rep.won_deals} won, {rep.lost_deals} lost, {rep.open_deals} open)\n")
    print(f"  Open pipeline value : {money(rep.open_value)}")
    print(f"  Weighted forecast   : {money(rep.weighted_forecast)}")
    print(f"  Decided win rate    : {rep.overall_win_rate * 100:.0f}%")

    by = by_stage(rep)
    print("\nWhy the forecast is $0 and not a crash:")
    for name in [s["stage"] for s in rep.stages if not s["terminal"]]:
        s = by[name]
        print(f"  '{name}': advance rate {s['advance_rate'] * 100:.0f}% -> "
              f"P(win) {s['p_win'] * 100:.0f}%")
    assert rep.weighted_forecast == 0.0, "a zero-win history must forecast $0"
    print("\nThe engine reports the pipeline is worth nothing rather than paint a")
    print("green number the history can't support. That is the point of the tool.")


if __name__ == "__main__":
    main()
