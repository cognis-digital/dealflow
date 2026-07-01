# 11 — Single-stage pipeline (edge case)

The smallest legal pipeline has one stage. DEALFLOW promotes the last
non-terminal stage to the won stage, so all three deals here land as "won" with
no open pipeline. Useful as a boundary check that the engine never divides by
zero or mislabels the win condition when the state machine is trivial.

Run:

    dealflow forecast -p demos/11-single-stage/pipeline.yml -d demos/11-single-stage/deals.csv
