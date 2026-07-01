"""Scenario 4 - Finance / forecasting in CI.

Finance wants the forecast to be a tripwire, not a vibe: if the committed
quarterly pipeline drops below the number the board was promised, the build
should fail and someone should know — automatically, on every push.

dealflow's CLI returns exit code 1 when a `--min-forecast` / `--min-win-rate`
gate fails (0 when it passes, 2 on a data error), so it drops straight into CI.
This demo drives the real CLI entry point and shows both outcomes offline.
"""
from _common import money, rule, sample

from dealflow.cli import main as cli_main


def main() -> None:
    rule("FINANCE CI GATE  -  fail the build when the forecast slips")
    pipe, deals = sample("05-quarterly-gate")

    base = ["forecast", "-p", pipe, "-d", deals, "--format", "json"]

    # Establish the current number quietly via the public API.
    from dealflow.core import analyze, load_deals, load_pipeline
    rep = analyze(load_pipeline(pipe), load_deals(deals))
    print(f"\nPipeline: {rep.pipeline}")
    print(f"Current weighted forecast: {money(rep.weighted_forecast)}  "
          f"(win rate {rep.overall_win_rate * 100:.0f}%)")

    target_ok = 50_000
    target_high = 100_000

    print(f"\n1) CI gate at {money(target_ok)} (a realistic floor):")
    rc = _quiet_gate(base, target_ok)
    print(f"   exit code = {rc}  ->  {'PASS — build proceeds' if rc == 0 else 'FAIL'}")
    assert rc == 0, "expected the realistic gate to pass"

    print(f"\n2) CI gate at {money(target_high)} (board target the pipeline can't cover):")
    rc = _quiet_gate(base, target_high)
    print(f"   exit code = {rc}  ->  {'PASS' if rc == 0 else 'FAIL — build red, forecast below target'}")
    assert rc == 1, "expected the aggressive gate to fail"

    print("\nIn a CI YAML this is one line:")
    print("    dealflow forecast -p pipeline.yml -d deals.csv --min-forecast 100000")
    print("A red build is now the same signal as a failing test — the forecast")
    print("can no longer silently erode between board meetings.")


def _quiet_gate(base: list[str], floor: int) -> int:
    """Run the real CLI with a forecast gate, suppressing its stdout/stderr."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return cli_main(base + ["--min-forecast", str(floor)])


if __name__ == "__main__":
    main()
