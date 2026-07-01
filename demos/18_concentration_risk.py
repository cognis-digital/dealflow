"""Scenario 18 - Is the forecast propped up by one whale?

A weighted forecast can look healthy while resting almost entirely on a single
large, still-open deal. If that one deal slips, the number collapses. dealflow
reports `concentration` — the share of the weighted forecast carried by the
single largest open deal — and offers a `--max-concentration` CI gate to flag a
fragile pipeline. This drives the real API on the enterprise ACV sample.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("12-quoted-amounts")
    rule("CONCENTRATION RISK  -  how much of the number is one deal?")

    open_deals = sorted(
        (d for d in rep.deals if d["status"] == "open"),
        key=lambda d: d["expected_value"], reverse=True,
    )

    print(f"\nPipeline: {rep.pipeline}")
    print(f"Weighted forecast   : {money(rep.weighted_forecast)}")
    print(f"Top-deal concentration: {rep.concentration * 100:.0f}%\n")

    print("  Open deals by expected value:")
    for d in open_deals:
        share = (d["expected_value"] / rep.weighted_forecast * 100) if rep.weighted_forecast else 0
        print(f"    {d['deal_id']:<6}{money(d['expected_value']):>12}  ({share:.0f}% of forecast)")

    if open_deals:
        top = open_deals[0]
        print(f"\nIf '{top['deal_id']}' slips, {rep.concentration * 100:.0f}% of the "
              f"forecast ({money(top['expected_value'])}) evaporates.")
    print("\nGate a fragile forecast in CI:")
    print("    dealflow forecast -p p.yml -d d.csv --max-concentration 0.5")
    print("A red build says: diversify the pipeline before committing this number.")


if __name__ == "__main__":
    main()
