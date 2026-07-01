"""Scenario 8 - Stitching multi-CRM exports with messy dates and money.

When you merge exports from different systems/regions you get a soup of date
formats (YYYY-MM-DD, MM/DD/YYYY, ...) and money strings ("$45,000"). dealflow's
loader normalizes all of them so you don't have to pre-clean the file. This runs
the 09-mixed-dateformats sample and proves the numbers land correctly.
"""
from _common import load, money, rule


def main() -> None:
    pipeline, rep = load("09-mixed-dateformats")
    rule("MULTI-CRM MERGE  -  messy dates & money, one clean forecast")

    print(f"\nPipeline: {rep.pipeline}   ({rep.total_deals} deals)\n")
    print("The loader accepted several date formats in the SAME file and parsed")
    print("currency-formatted amounts like \"$45,000\" without pre-cleaning.\n")
    print(f"  Won value (closed)  : {money(rep.won_value)}")
    print(f"  Open pipeline value : {money(rep.open_value)}")
    print(f"  Weighted forecast   : {money(rep.weighted_forecast)}")
    print(f"  Decided win rate    : {rep.overall_win_rate * 100:.0f}%")

    # velocity proves the dates were read (not silently dropped)
    timed = [s for s in rep.stages if s["avg_days_in_stage"] is not None]
    print("\nVelocity (proves the mixed date formats were read, not dropped):")
    for s in timed:
        print(f"  {s['stage']:<12} avg {s['avg_days_in_stage']:.1f} days in stage")


if __name__ == "__main__":
    main()
