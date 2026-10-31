# Link pairs: finance_v1 · rule · split test

Pairs: 406 from `bench/data/finance_v1/pairs.jsonl` (sha256 dcda96819707…). Query: the dependent is the new memory, the other the only candidate; ids are opaque. Abstentions (invalid output): 0.

Cost: 0.000193 s wall and 0.000077 s process CPU per linker call (406 calls, 0 LLM calls).

| stratum | n | tp | fp | fn | tn | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|---|---|---|---|
| overall | 406 | 24 | 32 | 48 | 302 | 0.429 | 0.333 | 0.375 | n/a |
| provenance=scenario | 406 | 24 | 32 | 48 | 302 | 0.429 | 0.333 | 0.375 | n/a |
| held_out=unknown | 406 | 24 | 32 | 48 | 302 | 0.429 | 0.333 | 0.375 | n/a |

False positives by negative kind:

- reversed edge: 0/72 (0.000)
- same structured key: 0/10 (0.000)
- unspecified: 32/252 (0.127)

Recall by gold link type (tp / tp+fn; * = no train pair of this type):

- alert_for*: 0/19 (0.000)
- depends_on_fact*: 0/5 (0.000)
- depends_on_time_period*: 0/5 (0.000)
- estimate_from*: 5/5 (1.000)
- journaled_with*: 0/4 (0.000)
- premise_of*: 19/34 (0.559)

Precision and F1 are n/a in a stratum without gold negatives (every RULE pair is a positive); read such a stratum for recall. held_out=both is the strict test cell (persona and template unseen). Typed metrics are n/a: this linker proposes one fixed type. Synthetic v0 data: harness numbers on a small regular track, not a headline result; a number is citable only from a run on a committed tree.
