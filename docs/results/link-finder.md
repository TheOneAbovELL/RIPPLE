# Link finder (C1): a trained pair classifier against the rule baseline, jobs and finance
Written 2026-10-31 (WS-19). Every number below comes from
results/2026-10-31_linkpairs_summary_uncommitted (written by `training.summarize` from
the ten run folders it lists) or from one of those run folders, named in the same
paragraph or table row (I8). The model, recipe and evaluation protocol are ADR-0125,
ADR-0126, ADR-0127 and ADR-0093.

## Read this first: what these numbers are and are not
- **Tiny synthetic data.** The jobs v0 pairs come from 35 generated scenarios with five
  invented personas (ADR-0090). The model was fitted on two personas and validated on a
  third; the counts are in section 2.
- **Silver labels, one labeller, no human check yet.** Jobs labels come from scenario
  files and structure rules (provenance `scenario` and `rule`); finance labels from the
  finance scenarios (ADR-0102). Nobody has hand-checked either (the 300-pair protocol,
  ADR-0092, is the author's). Every scenario was written by the same author, so the
  labels share one person's idea of what depends on what.
- **No LLM linker numbers.** There is no ANTHROPIC_API_KEY on this machine, so H3 cannot
  be judged (section 5). Nothing here compares the trained linker with the LLM linker.
- **Uncommitted code: nothing here is citable yet.** Every run says `git_sha:
  "uncommitted"`; the paper's macros refuse such runs (ADR-0110). Re-run (section 8)
  after the author's first commit before any paper or thesis use.
- **One call is one pair with one candidate** (ADR-0093). Cost per call is cost per
  scored pair, not cost per new memory with many candidates.

## 1. Data
| Track | File | Used for |
|---|---|---|
| jobs_v0 | training/data/jobs_v0_pairs.jsonl (sha256 cfee9ebb4d98…) | fit, validation, test |
| finance_v1 | bench/data/finance_v1/pairs.jsonl (sha256 dcda96819707…) | transfer test only |

The jobs split is by persona and template (test personas p3_esha, p4_bharat; test
templates cgpa_rise, deadline_moved). Decontamination removes only test pairs whose
*two* texts equal a training pair's (ADR-0091); the manifest
training/data/jobs_v0_pairs.manifest.json counts the test pairs that still share one
memory text with training (`counts.test_pairs_sharing_a_text_with_train`), about half
the test split. Shared texts help most where the template was seen (held_out=persona
and held_out=template), which is another reason to read held_out=both.

Class balance (gold links are tp + fn, pairs are n, in
results/2026-10-31_linkpairs_jobs_v0_rule_uncommitted/report.md and
results/2026-10-31_linkpairs_finance_v1_rule_uncommitted/report.md): the jobs test split
has 93 gold links in 392 pairs, of which held_out=both has 22 in 100, held_out=persona
38 in 140 and held_out=template 33 in 152; finance has 72 in 406. The primary cell rests
on 22 gold links, so one true positive more or less moves its recall by one twenty-second.

Finance pairs share no (parent, dependent) text pair and no single text with the jobs
training split (`transfer.pairs_sharing_a_text_with_train` in each finance run's
config.json). Of their six gold link types (alert_for, depends_on_fact,
depends_on_time_period, estimate_from, journaled_with, premise_of) only depends_on_fact
and depends_on_time_period are jobs types, so finance runs report untyped metrics only.

## 2. Model and training
- `answerdotai/ModernBERT-base` fine-tuned end to end with a linear head over the eight
  jobs classes (seven link types plus "none"), class-weighted cross-entropy, AdamW,
  10 epochs, on CPU (torch 2.15.0, transformers 5.22.1; ADR-0125, ADR-0126). The hub
  commit (8949b909ec90…) is recorded in the third run's config.json; the first two runs
  predate the revision lookup and record null. By the collaborator's local check the
  Hugging Face cache held only that one snapshot when all three trained.
- Input: `"[kind] content || subject attribute value"` for each memory, as a sentence pair
  (parent, dependent). Serving scores both orientations and proposes at most the more
  probable one (ADR-0126 point 7).
- Epoch and threshold were chosen on the validation persona p2_harsh by untyped F1. Each
  row's numbers are in its run folder's report.md ("Model:" and "Validation" lines):

| Seed | Run folder | Fitted / validated pairs | Chosen epoch | Threshold | Validation F1 | Training wall seconds |
|---|---|---|---|---|---|---|
| 20261031 | results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted | 128 / 72 | 9 | 0.5 | 0.973 | 934.2 |
| 20261032 | results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_2 | 128 / 72 | 9 | 0.5 | 1.000 | 777.8 |
| 20261033 | results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3 | 128 / 72 | 7 | 0.1 | 0.973 | 585.5 |

- A validation F1 near 1 says the validation persona is easy, not that the model is
  good: compare section 3. The choice is close to arbitrary. In
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3/report.md, epochs 7 to 10
  all reach validation F1 0.973; the tie rule keeps epoch 7, whose best threshold is
  0.1, while epochs 9 and 10 reach the same F1 at threshold 0.5. By the collaborator's
  account the first two runs shared the CPU with test runs, so their training times are
  upper bounds.

## 3. Results: jobs test split
Mean ± sample standard deviation over the three seeds (`--new dependent`); the rule
linker is deterministic (one run). Every value in this table is in
results/2026-10-31_linkpairs_summary_uncommitted/report.md.

| Cell (summary folder) | Rule F1 | Trained F1 | Trained precision | Trained recall | Trained typed F1 |
|---|---|---|---|---|---|
| held_out=both, primary (results/2026-10-31_linkpairs_summary_uncommitted) | 0.571 | 0.601 ± 0.096 | 0.574 ± 0.071 | 0.636 ± 0.136 | 0.491 ± 0.033 |
| held_out=template (results/2026-10-31_linkpairs_summary_uncommitted) | 0.562 | 0.607 ± 0.048 | 0.609 ± 0.033 | 0.616 ± 0.115 | 0.493 ± 0.059 |
| held_out=persona (results/2026-10-31_linkpairs_summary_uncommitted) | 0.245 | 0.874 ± 0.034 | 0.968 ± 0.002 | 0.798 ± 0.055 | 0.874 ± 0.034 |
| overall (results/2026-10-31_linkpairs_summary_uncommitted) | 0.465 | 0.709 ± 0.041 | 0.726 ± 0.042 | 0.695 ± 0.070 | 0.638 ± 0.039 |

The rule linker proposes one fixed type, so it has no typed F1. Its precision and recall
on held_out=both are 0.600 and 0.545 (results/2026-10-31_linkpairs_jobs_v0_rule_uncommitted).

Reading:
- **On the strict cell there is no evidence of a difference.** The trained mean is above
  the rule linker by less than one seed standard deviation, on 22 gold links; per seed the
  held_out=both F1 is 0.524, 0.708 and 0.571 (results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_2,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3): one seed below the rule, one
  equal, one above. No test was run, and no claim that the trained linker beats the rules
  on unseen personas *and* templates follows from this.
- **The gain is on unseen personas with seen templates**: the model learns the
  templates' wording, which the rules miss (rule recall in that cell is 0.158,
  results/2026-10-31_linkpairs_jobs_v0_rule_uncommitted). That is template memorisation as
  much as dependency induction, and it is why held_out=both is the cell to read.
- **By provenance**, on `scenario` pairs (the links no structure rule derives, plus all
  negatives) trained F1 is 0.674, 0.638 and 0.594 against the rule's 0.114; on `rule`
  pairs (positives only, so read recall) trained recall is 0.528, 0.774 and 0.660 against
  the rule's 0.604 (results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_2,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3,
  results/2026-10-31_linkpairs_jobs_v0_rule_uncommitted).
- **Direction:** no seed proposed a reversed link (0/93 reversed-link negatives); the false
  positives are all "same scenario, no link": 19/206, 24/206 and 31/206
  (results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_2,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3).
- **Unseen type:** `criteria_from` has no fitted pair; the seeds found 0/10, 8/10 and 0/10
  of its test links, untyped (results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_2,
  results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3).
- **Orientation:** the `--new parent` run of seed 20261031
  (results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_4) has the same confusion
  counts as its `--new dependent` run, as expected for a linker that scores both
  orientations. The rule linker also gives the same counts both ways on this file
  (results/2026-10-31_linkpairs_jobs_v0_rule_uncommitted_2).

## 4. Results: finance transfer (H4)
The model was trained on jobs and scored with `--transfer` on all 406 finance pairs.

| Linker (folder) | Precision | Recall | F1 |
|---|---|---|---|
| Rule (results/2026-10-31_linkpairs_finance_v1_rule_uncommitted) | 0.429 | 0.333 | 0.375 |
| Trained, three seeds (results/2026-10-31_linkpairs_summary_uncommitted) | see below | 0.014 ± 0.024 | 0.027 ± 0.046 |

Per seed the trained linker made 0, 1 and 3 link predictions and found 0, 0 and 3 of the
72 finance links, F1 0.000, 0.000 and 0.080 (tp, fp and fn in
results/2026-10-31_linkpairs_finance_v1_trained_uncommitted,
results/2026-10-31_linkpairs_finance_v1_trained_uncommitted_2 and
results/2026-10-31_linkpairs_finance_v1_trained_uncommitted_3). A mean precision over one
and three predictions means nothing, so none is given. The three true positives are all
depends_on_time_period, a jobs type: 3/5 of that type's finance links
(results/2026-10-31_linkpairs_finance_v1_trained_uncommitted_3). The rule linker's true
positives are estimate_from 5/5 and premise_of 19/34, and it found 0/5 of each shared type
(results/2026-10-31_linkpairs_finance_v1_rule_uncommitted).

**H4 reading: not supported on this evidence.** "Modest drop" has no numeric target yet
(docs/04). Still, an F1 that falls from the strict jobs cell's level (section 3) to near zero on
finance, far below the rule linker on the same file, is not modest under any reading.
These runs do not separate the possible causes:
- the fitted pairs come from a handful of jobs templates;
- finance wording shares no text with jobs;
- four of the six finance link types do not exist in the label space, so for those the
  model can only answer "none" or a jobs relation (and even the shared types were mostly
  missed).

Nor do these runs establish why the rule linker does better here. Its hits are pairs
where the dependent's text mentions the parent fact's attribute or value, which is its
rule (src/ripple/linking/rules.py).

## 5. H3 status: pending the key
H3 needs the LLM linker on the same pair file, both orientations, with its cost. It has
not been run, because there is no ANTHROPIC_API_KEY here. With a key and
`config/llm.default.toml` (or `RIPPLE_LLM_CONFIG`):

```bash
uv run python -m training.evaluate --linker llm
uv run python -m training.evaluate --linker llm --new parent
uv run python -m training.evaluate --linker llm --pairs bench/data/finance_v1/pairs.jsonl
```

Then add the new folders to `uv run python -m training.summarize ...` with the ten
above.
- LLM accuracy: pending the key.
- LLM cost: pending the key, and pending per-call usage from the LLM linker (metrics.json
  records calls, not tokens or USD; this is WS-14's open request).

The default linker therefore stays the LLM linker (ADR-0128).

## 6. Cost of the trained linker
Process CPU time counts all threads of the process (`time.process_time`), so it can
exceed wall time times `torch_threads` (6): tokenizer and runtime threads count too. The
processor ("AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD", Windows 11) is recorded
in each run folder. Means per call from the summary:

| Linker (folder) | Wall seconds per call | CPU seconds per call |
|---|---|---|
| Rule, jobs (results/2026-10-31_linkpairs_summary_uncommitted) | 0.000228 | 0.000080 |
| Trained, jobs, three seeds (results/2026-10-31_linkpairs_summary_uncommitted) | 0.297283 | 1.661604 |
| Trained, finance, three seeds (results/2026-10-31_linkpairs_summary_uncommitted) | 0.254222 | 1.570813 |

Wall time depends on load: the machine was shared with other sessions. Per jobs run the
trained linker's wall seconds per call were 0.247472, 0.214084 and 0.430292
(results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted,
results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_2,
results/2026-10-31_linkpairs_jobs_v0_trained_uncommitted_3), so read the means as an
order of magnitude.

Each call scores two sequences (both orientations) with the ModernBERT-base encoder. The
trained linker costs no API money, but on CPU it is hundreds to thousands of times slower
than the rules by wall time and over ten thousand times slower by CPU time (ratios of the
rows above). Whether that is "a fraction of the cost" of the LLM linker is the H3
question, which waits for section 5.

## 7. Limitations
- The data is tiny, synthetic and single-author. The labels are silver and nobody has
  checked them. The primary cell has 100 pairs and 22 gold links.
- Three seeds measure training noise only, not data noise. There are no confidence
  intervals over personas (ADR-0093 consequence 1).
- Validation used one persona with a few dozen pairs. It chose thresholds from 0.1 to
  0.5 across seeds, with ties across epochs (section 2), so the epoch and threshold
  choice is close to arbitrary at this size.
- One fixed negative ratio sets precision: 3:1 for jobs, and whatever the templates give
  for finance.
- The trained linker is scored pair by pair. Write-time use, with many candidates per new
  memory, is not measured.
- Results are from an uncommitted tree; re-run after the first commit before citing.

## 8. Reproduce
```bash
uv run python -m training.train --validation-persona p2_harsh --seed 20261031
uv run python -m training.train --validation-persona p2_harsh --seed 20261032
uv run python -m training.train --validation-persona p2_harsh --seed 20261033
uv run python -m training.evaluate --linker rule
uv run python -m training.evaluate --linker rule --new parent
uv run python -m training.evaluate --linker rule --pairs bench/data/finance_v1/pairs.jsonl
uv run python -m training.evaluate --linker trained --model training/artifacts/modernbert-base_seed20261031
uv run python -m training.evaluate --linker trained --model training/artifacts/modernbert-base_seed20261031 --new parent
uv run python -m training.evaluate --linker trained --model training/artifacts/modernbert-base_seed20261031 --pairs bench/data/finance_v1/pairs.jsonl --transfer
uv run python -m training.summarize results/<the ten folders>
```
(The trained `evaluate` lines repeat for seeds 20261032 and 20261033, without
`--new parent`.)
