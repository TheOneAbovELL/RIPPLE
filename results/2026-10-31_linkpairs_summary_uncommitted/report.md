# Link pairs: summary over runs

mean ± sample standard deviation over the runs listed (one value: no spread; (n=k): only k runs define the metric, e.g. precision with no predicted link). Read held_out=both for H3 on the jobs track. n/a: undefined in that cell (no gold negatives, or typed metrics off).

## rule · finance_v1 · split test · new dependent (1 runs)

Runs: `results/2026-10-31_linkpairs_finance_v1_rule_uncommitted`

| cell | pairs | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|
| held_out=unknown | 406 | 0.429 | 0.333 | 0.375 | n/a |
| overall | 406 | 0.429 | 0.333 | 0.375 | n/a |

Cost per call: wall 0.000193 s, process CPU 0.000077 s.

## rule · jobs_v0 · split test · new dependent (1 runs)

Runs: `results/2026-10-31_linkpairs_jobs_v0_rule_uncommitted`

| cell | pairs | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|
| held_out=both | 100 | 0.600 | 0.545 | 0.571 | n/a |
| held_out=persona | 140 | 0.545 | 0.158 | 0.245 | n/a |
| held_out=template | 152 | 0.581 | 0.545 | 0.562 | n/a |
| overall | 392 | 0.581 | 0.387 | 0.465 | n/a |

Cost per call: wall 0.000228 s, process CPU 0.000080 s.

## rule · jobs_v0 · split test · new parent (1 runs)

Runs: `results/2026-10-31_linkpairs_jobs_v0_rule_uncommitted_2`

| cell | pairs | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|
| held_out=both | 100 | 0.600 | 0.545 | 0.571 | n/a |
| held_out=persona | 140 | 0.545 | 0.158 | 0.245 | n/a |
| held_out=template | 152 | 0.581 | 0.545 | 0.562 | n/a |
| overall | 392 | 0.581 | 0.387 | 0.465 | n/a |

Cost per call: wall 0.000118 s, process CPU 0.000120 s.

## trained (answerdotai/ModernBERT-base) · transfer · finance_v1 · split test · new dependent (3 runs)

Runs: `results/2026-10-31_linkpairs_finance_v1_trained_uncommitted`, `results/2026-10-31_linkpairs_finance_v1_trained_uncommitted_2`, `results/2026-10-31_linkpairs_finance_v1_trained_uncommitted_3`

| cell | pairs | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|
| held_out=unknown | 406 | 0.500 ± 0.707 (n=2) | 0.014 ± 0.024 | 0.027 ± 0.046 | n/a |
| overall | 406 | 0.500 ± 0.707 (n=2) | 0.014 ± 0.024 | 0.027 ± 0.046 | n/a |

Cost per call: wall 0.254222 s, process CPU 1.570813 s.

## trained (answerdotai/ModernBERT-base) · jobs_v0 · split test · new dependent (3 runs)

Runs: `results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted`, `results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_2`, `results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3`

| cell | pairs | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|
| held_out=both | 100 | 0.574 ± 0.071 | 0.636 ± 0.136 | 0.601 ± 0.096 | 0.491 ± 0.033 |
| held_out=persona | 140 | 0.968 ± 0.002 | 0.798 ± 0.055 | 0.874 ± 0.034 | 0.874 ± 0.034 |
| held_out=template | 152 | 0.609 ± 0.033 | 0.616 ± 0.115 | 0.607 ± 0.048 | 0.493 ± 0.059 |
| overall | 392 | 0.726 ± 0.042 | 0.695 ± 0.070 | 0.709 ± 0.041 | 0.638 ± 0.039 |

Cost per call: wall 0.297283 s, process CPU 1.661604 s.

## trained (answerdotai/ModernBERT-base) · jobs_v0 · split test · new parent (1 runs)

Runs: `results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_4`

| cell | pairs | precision | recall | F1 | typed F1 |
|---|---|---|---|---|---|
| held_out=both | 100 | 0.550 | 0.500 | 0.524 | 0.524 |
| held_out=persona | 140 | 0.969 | 0.816 | 0.886 | 0.886 |
| held_out=template | 152 | 0.640 | 0.485 | 0.552 | 0.552 |
| overall | 392 | 0.753 | 0.624 | 0.682 | 0.682 |

Cost per call: wall 0.547424 s, process CPU 1.905971 s.
