# Link pairs: jobs_v0 · trained · split test

Pairs: 392 from `training/data/jobs_v0_pairs.jsonl` (sha256 cfee9ebb4d98…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

Model: `answerdotai/ModernBERT-base`, seed 20261033, threshold 0.1 (validation personas), chosen epoch 7; fitted on 128 pairs, validated on 72 pairs of personas ['p2_harsh']; training took 585.5 s wall.
Validation at the chosen epoch: F1 0.973, precision 0.947, recall 1.000.
Validation per epoch (best threshold each): epoch 1: F1 0.606 at threshold 0.25; epoch 2: F1 0.688 at threshold 0.5; epoch 3: F1 0.857 at threshold 0.15; epoch 4: F1 0.909 at threshold 0.85; epoch 5: F1 0.900 at threshold 0.25; epoch 6: F1 0.947 at threshold 0.75; epoch 7: F1 0.973 at threshold 0.1; epoch 8: F1 0.973 at threshold 0.7; epoch 9: F1 0.973 at threshold 0.5; epoch 10: F1 0.973 at threshold 0.5.

Cost: 0.430292 s wall and 1.760403 s process CPU per linker call (392 calls, 0 LLM calls).

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 392 | 65 | 31 | 28 | 268 | 0.677 | 0.699 | 0.688 | 0.614 |
| provenance=rule | 53 | 35 | 0 | 18 | 0 | n/a | 0.660 | n/a | n/a |
| provenance=scenario | 339 | 30 | 31 | 10 | 268 | 0.492 | 0.750 | 0.594 | 0.594 |
| held_out=both | 100 | 14 | 13 | 8 | 65 | 0.519 | 0.636 | 0.571 | 0.490 |
| held_out=persona | 140 | 28 | 1 | 10 | 101 | 0.966 | 0.737 | 0.836 | 0.836 |
| held_out=template | 152 | 23 | 17 | 10 | 102 | 0.575 | 0.697 | 0.630 | 0.493 |

False positives by negative kind:

- reversed link: 0/93 (0.000)
- same scenario, no link: 31/206 (0.150)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- criteria_from*: 0/10 (0.000)
- depends_on_fact: 7/16 (0.438)
- depends_on_time_period: 2/2 (1.000)
- eligibility_of: 42/42 (1.000)
- fit_of: 1/2 (0.500)
- reminder_for: 11/19 (0.579)
- sent_with_resume: 2/2 (1.000)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
