"""Scenario 15 - Coherence at volume (60 deals, 5 open stages).

The same invariants that hold on the tiny demos must hold on a realistic log.
This runs the 16-large-pipeline sample and asserts, on 60 deals through a
five-open-stage funnel, that advanced <= entered per stage, P(win) is
non-decreasing along the open stages, and per-deal expected values reconcile to
the reported weighted forecast.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("16-large-pipeline")
    rule("SCALE / COHERENCE  -  60 deals, invariants intact")

    open_stages = [s for s in rep.stages if not s["terminal"]]
    print(f"\nPipeline: {rep.pipeline}   ({rep.total_deals} deals)\n")
    print("  STAGE           ENTERED   ADVANCED   ADVANCE%   P(WIN)")
    print("  " + "-" * 56)
    prev_pwin = -1.0
    for s in open_stages:
        assert s["advanced"] <= s["entered"], "advanced can never exceed entered"
        assert s["p_win"] + 1e-9 >= prev_pwin, "P(win) must be non-decreasing"
        prev_pwin = s["p_win"]
        print(f"  {s['stage']:<15}{s['entered']:>6}{s['advanced']:>11}"
              f"{s['advance_rate'] * 100:>10.0f}%{s['p_win'] * 100:>8.0f}%")

    ev_sum = sum(d["expected_value"] for d in rep.deals)
    assert abs(ev_sum - rep.weighted_forecast) < 0.5, "forecast must reconcile"

    print(f"\n  Deals: {rep.open_deals} open / {rep.won_deals} won / {rep.lost_deals} lost")
    print(f"  Open pipeline value : {money(rep.open_value)}")
    print(f"  Weighted forecast   : {money(rep.weighted_forecast)}")
    print("\nInvariants verified at volume: advanced<=entered, P(win) monotone,")
    print("and sum(expected_value) reconciles to the weighted forecast.")


if __name__ == "__main__":
    main()
