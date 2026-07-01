"""Scenario 17 - Guarding win-rate, not just dollars, in CI.

A forecast can look healthy in dollars while resting on a handful of oversized,
low-probability deals. The --min-win-rate gate catches that: it fails the build
when the decided win rate drops below a floor, independent of the dollar
forecast. This demo drives the real CLI on the 02-saas-monthly sample and shows
both a passing and a failing win-rate gate.
"""
import contextlib
import io

from _common import rule, sample
from dealflow.cli import main as cli_main
from dealflow.core import analyze, load_deals, load_pipeline


def _quiet(argv) -> int:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return cli_main(argv)


def main() -> None:
    rule("WIN-RATE GATE  -  fail on quality, not just quantity")
    pipe, deals = sample("02-saas-monthly")
    rep = analyze(load_pipeline(pipe), load_deals(deals))
    wr = rep.overall_win_rate

    print(f"\nPipeline: {rep.pipeline}")
    print(f"Decided win rate: {wr * 100:.1f}%  "
          f"({rep.won_deals} won / {rep.won_deals + rep.lost_deals} decided)\n")

    base = ["forecast", "-p", pipe, "-d", deals]

    low = round(max(0.0, wr - 0.2), 2)
    high = round(min(1.0, wr + 0.2), 2)

    rc_ok = _quiet(base + ["--min-win-rate", str(low)])
    print(f"1) --min-win-rate {low}  -> exit {rc_ok}  "
          f"({'PASS' if rc_ok == 0 else 'FAIL'})")
    assert rc_ok == 0

    rc_fail = _quiet(base + ["--min-win-rate", str(high)])
    print(f"2) --min-win-rate {high}  -> exit {rc_fail}  "
          f"({'PASS' if rc_fail == 0 else 'FAIL — win rate below floor'})")
    assert rc_fail == 1

    print("\nCombine both gates in CI to block a merge when EITHER the dollar")
    print("forecast slips or the win rate erodes:")
    print("    dealflow forecast -p p.yml -d d.csv --min-forecast 100000 --min-win-rate 0.5")


if __name__ == "__main__":
    main()
