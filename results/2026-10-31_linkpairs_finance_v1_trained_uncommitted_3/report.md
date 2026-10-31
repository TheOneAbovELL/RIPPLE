# Link pairs: finance_v1 · trained · split test

Pairs: 406 from `bench/data/finance_v1/pairs.jsonl` (sha256 dcda96819707…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

**Transfer run (H4):** a model trained on `training/data/jobs_v0_pairs.jsonl` scored on another track's test pairs; no evaluated text pair equals a training one, 0 pairs share one text with training.

Model: `answerdotai/ModernBERT-base`, seed 20261033, threshold 0.1 (validation personas), chosen epoch 7; fitted on 128 pairs, validated on 72 pairs of personas ['p2_harsh']; training took 585.5 s wall.
Validation at the chosen epoch: F1 0.973, precision 0.947, recall 1.000.
Validation per epoch (best threshold each): epoch 1: F1 0.606 at threshold 0.25; epoch 2: F1 0.688 at threshold 0.5; epoch 3: F1 0.857 at threshold 0.15; epoch 4: F1 0.909 at threshold 0.85; epoch 5: F1 0.900 at threshold 0.25; epoch 6: F1 0.947 at threshold 0.75; epoch 7: F1 0.973 at threshold 0.1; epoch 8: F1 0.973 at threshold 0.7; epoch 9: F1 0.973 at threshold 0.5; epoch 10: F1 0.973 at threshold 0.5.

Cost: 0.238931 s wall and 1.590440 s process CPU per linker call (406 calls, 0 LLM calls).

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 406 | 3 | 0 | 69 | 334 | 1.000 | 0.042 | 0.080 | n/a |
| provenance=scenario | 406 | 3 | 0 | 69 | 334 | 1.000 | 0.042 | 0.080 | n/a |
| held_out=unknown | 406 | 3 | 0 | 69 | 334 | 1.000 | 0.042 | 0.080 | n/a |

False positives by negative kind:

- reversed edge: 0/72 (0.000)
- same structured key: 0/10 (0.000)
- unspecified: 0/252 (0.000)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- alert_for*: 0/19 (0.000)
- depends_on_fact: 0/5 (0.000)
- depends_on_time_period: 3/5 (0.600)
- estimate_from*: 0/5 (0.000)
- journaled_with*: 0/4 (0.000)
- premise_of*: 0/34 (0.000)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Typed metrics are n/a: this track's link types are outside the model's label space. Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
