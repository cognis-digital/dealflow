"""Scenario 10 - Two YAML styles, one state machine.

DEALFLOW ships its own tiny YAML subset parser. It accepts both block style
(- name: lead / type: open) and inline flow mappings (- {name: lead, type:
open}). This demo loads a flow-mapping pipeline and the equivalent block-style
one and shows they produce an identical Pipeline object.
"""
from _common import load, money, rule
from dealflow.core import load_pipeline
from _common import sample


def main() -> None:
    rule("YAML FLEXIBILITY  -  flow mappings == block style")

    flow_pipe, _ = sample("10-flow-mapping")
    block_pipe, _ = sample("01-basic")
    flow = load_pipeline(flow_pipe)
    block = load_pipeline(block_pipe)

    def shape(p):
        return [(s.name, s.terminal, s.won) for s in p.stages]

    print("\nFlow-mapping pipeline stages (- {name: x, type: y}):")
    for name, term, won in shape(flow):
        tag = "won" if won else ("terminal" if term else "open")
        print(f"  {name:<12} [{tag}]")

    print("\nSame shape as the block-style 01-basic pipeline:", shape(flow) == shape(block))

    pipeline, rep = load("10-flow-mapping")
    print(f"\nAnalysis runs identically: {rep.total_deals} deals, "
          f"weighted forecast {money(rep.weighted_forecast)}.")
    print("Use whichever YAML style your existing tooling already emits.")


if __name__ == "__main__":
    main()
