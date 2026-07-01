"""Scenario 12 - Seven-figure enterprise ACV with formatted money.

Enterprise pipelines carry big, messily-formatted numbers: "$1,250,000".
dealflow parses them and produces a weighted forecast where a single deal's
probability swing moves the number materially. This runs the 12-quoted-amounts
sample and shows the per-deal contribution to the forecast.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("12-quoted-amounts")
    rule("ENTERPRISE ACV  -  seven-figure deals, formatted money")

    print(f"\nPipeline: {rep.pipeline}   ({rep.total_deals} deals)\n")
    print(f"  Won value (closed)  : {money(rep.won_value)}")
    print(f"  Open pipeline value : {money(rep.open_value)}")
    print(f"  Weighted forecast   : {money(rep.weighted_forecast)}\n")

    print("  DEAL   STAGE           AMOUNT        P(WIN)   EXP_VALUE")
    print("  " + "-" * 56)
    for d in sorted(rep.deals, key=lambda x: x["amount"], reverse=True):
        print(f"  {d['deal_id']:<7}{d['current_stage']:<14}{money(d['amount']):>12}"
              f"{d['p_win'] * 100:>8.0f}%{money(d['expected_value']):>12}")

    open_deals = [d for d in rep.deals if d["status"] == "open"]
    if open_deals:
        biggest = max(open_deals, key=lambda d: d["expected_value"])
        print(f"\nLargest expected-value open deal: {biggest['deal_id']} at "
              f"{money(biggest['expected_value'])}. Currency symbols and commas in")
        print("the source file were normalized automatically by the loader.")


if __name__ == "__main__":
    main()
