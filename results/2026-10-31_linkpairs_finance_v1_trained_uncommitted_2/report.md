# Link pairs: finance_v1 · trained · split test

Pairs: 406 from `bench/data/finance_v1/pairs.jsonl` (sha256 dcda96819707…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

**Transfer run (H4):** a model trained on `training/data/jobs_v0_pairs.jsonl` scored on another track's test pairs; no evaluated text pair equals a training one, 0 pairs share one text with training.

Model: `answerdotai/ModernBERT-base`, seed 20261032, threshold 0.5 (validation personas), chosen epoch 9; fitted on 128 pairs, validated on 72 pairs of personas ['p2_harsh']; training took 777.8 s wall.
Validation at the chosen epoch: F1 1.000, precision 1.000, recall 1.000.
Validation per epoch (best threshold each): epoch 1: F1 0.560 at threshold 0.1; epoch 2: F1 0.667 at threshold 0.4; epoch 3: F1 0.872 at threshold 0.9; epoch 4: F1 0.889 at threshold 0.5; epoch 5: F1 0.914 at threshold 0.8; epoch 6: F1 0.923 at threshold 0.5; epoch 7: F1 0.973 at threshold 0.35; epoch 8: F1 0.947 at threshold 0.5; epoch 9: F1 1.000 at threshold 0.5; epoch 10: F1 1.000 at threshold 0.5.

Cost: 0.271187 s wall and 1.569196 s process CPU per linker call (406 calls, 0 LLM calls).

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 406 | 0 | 1 | 72 | 333 | 0.000 | 0.000 | 0.000 | n/a |
| provenance=scenario | 406 | 0 | 1 | 72 | 333 | 0.000 | 0.000 | 0.000 | n/a |
| held_out=unknown | 406 | 0 | 1 | 72 | 333 | 0.000 | 0.000 | 0.000 | n/a |

False positives by negative kind:

- reversed edge: 1/72 (0.014)
- same structured key: 0/10 (0.000)
- unspecified: 0/252 (0.000)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- alert_for*: 0/19 (0.000)
- depends_on_fact: 0/5 (0.000)
- depends_on_time_period: 0/5 (0.000)
- estimate_from*: 0/5 (0.000)
- journaled_with*: 0/4 (0.000)
- premise_of*: 0/34 (0.000)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Typed metrics are n/a: this track's link types are outside the model's label space. Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
