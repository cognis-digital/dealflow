# 16 — Wide funnel at volume

Sixty deals through a five-open-stage enterprise pipeline. This scenario is a
scale/coherence check: every stage row's `advanced` count never exceeds its
`entered` count, P(win) is non-decreasing along the open stages, and the
per-deal expected values sum back to the reported weighted forecast — the same
invariants that hold on the tiny demos, now on a realistic log.

Run:

    dealflow forecast -p demos/16-large-pipeline/pipeline.yml -d demos/16-large-pipeline/deals.csv
