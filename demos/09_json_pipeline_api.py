"""Scenario 9 - Consuming the JSON report programmatically.

The forecast is a data artifact, not just a table. dealflow's Report.to_dict()
(the same structure the CLI emits with --format json) drops straight into any
downstream system: a dashboard, a Slack bot, another script. This demo builds
the report via the public API and treats it as JSON, asserting the invariants a
consumer can rely on.
"""
import json

from _common import money, rule
from dealflow.core import analyze, load_deals, load_pipeline
from _common import sample


def main() -> None:
    rule("JSON REPORT API  -  the forecast as machine-readable data")

    pipe, deals = sample("02-saas-monthly")
    rep = analyze(load_pipeline(pipe), load_deals(deals))
    doc = rep.to_dict()

    # Round-trip through JSON exactly as a downstream consumer would.
    doc = json.loads(json.dumps(doc))

    print(f"\nTop-level keys a consumer gets: {', '.join(sorted(doc))}\n")
    print(f"  pipeline           : {doc['pipeline']}")
    print(f"  total / open deals : {doc['total_deals']} / {doc['open_deals']}")
    print(f"  weighted_forecast  : {money(doc['weighted_forecast'])}")
    print(f"  overall_win_rate   : {doc['overall_win_rate']}")

    # Invariants a downstream system can trust:
    assert doc["total_deals"] == doc["open_deals"] + doc["won_deals"] + doc["lost_deals"]
    assert 0.0 <= doc["overall_win_rate"] <= 1.0
    assert len(doc["deals"]) == doc["total_deals"]
    assert doc["weighted_forecast"] <= doc["open_value"] + 0.01

    print("\nInvariants held (consumer-safe):")
    print("  - total = open + won + lost")
    print("  - 0 <= win_rate <= 1")
    print("  - one deal row per deal on file")
    print("  - weighted forecast never exceeds raw open pipeline value")


if __name__ == "__main__":
    main()
