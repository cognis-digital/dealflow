# 10 — Inline flow-mapping pipeline

The pipeline is written with YAML inline flow mappings
(`- {name: lead, type: open}`) rather than block style. DEALFLOW's built-in
YAML subset parser accepts both and builds the same state machine, so teams can
use whichever style their existing tooling emits.

Run:

    dealflow forecast -p demos/10-flow-mapping/pipeline.yml -d demos/10-flow-mapping/deals.csv
