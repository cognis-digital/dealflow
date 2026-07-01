"""Scenario 6 - Sales managers hunting stalled deals.

A deal that hasn't moved in weeks is quietly dying. dealflow surfaces the
oldest open deals by age_days so a manager can chase or disqualify them before
they rot off the forecast. This runs against the 06-stalled-deals sample, whose
negotiation stage holds two long-in-the-tooth deals.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("06-stalled-deals")
    rule("STALLED-DEAL HUNT  -  what hasn't moved, and for how long")

    open_deals = [d for d in rep.deals if d["status"] == "open"]
    open_deals.sort(key=lambda d: d["age_days"], reverse=True)

    print(f"\nPipeline: {rep.pipeline}   |   open deals: {len(open_deals)}\n")
    print("  DEAL          STAGE             AGE_DAYS   AMOUNT     EXP_VALUE")
    print("  " + "-" * 60)
    for d in open_deals:
        print(f"  {d['deal_id']:<13}{d['current_stage']:<16}{d['age_days']:>9}"
              f"{money(d['amount']):>12}{money(d['expected_value']):>13}")

    oldest = open_deals[0]
    print(f"\nMost stalled: {oldest['deal_id']} — {oldest['age_days']} days open in "
          f"'{oldest['current_stage']}'.")
    print("Rule of thumb: a deal older than 2x the average cycle either needs a")
    print("forcing event this week or should be pushed out of the committed number.")
    print(f"\nOpen pipeline: {money(rep.open_value)}  |  "
          f"weighted forecast: {money(rep.weighted_forecast)}")


if __name__ == "__main__":
    main()
