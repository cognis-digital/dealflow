# 14 — Zero-win quarter (edge case)

No deal ever reached `won`; three are lost and one is still open in `pitch`.
The historical advance rate into the win stage is zero, so the open deal's
P(win) is zero and the weighted forecast is `$0` — not a crash or a divide-by-
zero. This is the honest-math boundary: DEALFLOW will tell you the pipeline is
worth nothing rather than invent value.

Run:

    dealflow forecast -p demos/14-all-lost/pipeline.yml -d demos/14-all-lost/deals.csv
