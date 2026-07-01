"""Scenario 14 - When reps forget to fill in the deal size.

Real CRM data is incomplete. Some deals have an amount, some leave it blank.
dealflow counts every deal for conversion and velocity regardless, and treats a
missing amount as $0 dollar value so the forecast stays honest without dropping
the deal from the funnel. This runs the 15-partial-amounts sample.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("15-partial-amounts")
    rule("PARTIAL AMOUNTS  -  missing deal sizes don't break the funnel")

    print(f"\nPipeline: {rep.pipeline}   ({rep.total_deals} deals)\n")
    print("  DEAL   STATUS   AMOUNT       COUNTS FOR CONVERSION?")
    print("  " + "-" * 50)
    for d in rep.deals:
        counts = "yes"  # every deal is counted regardless of amount
        print(f"  {d['deal_id']:<7}{d['status']:<9}{money(d['amount']):>10}"
              f"{counts:>12}")

    zero_amt = [d for d in rep.deals if d["amount"] == 0]
    print(f"\n{len(zero_amt)} deal(s) have no amount -> contribute $0 to value but")
    print("still shape the advance rates and velocity.")
    print(f"\n  Open pipeline value : {money(rep.open_value)}")
    print(f"  Weighted forecast   : {money(rep.weighted_forecast)}")


if __name__ == "__main__":
    main()
