# Paper outline: Ripple — learned dependency links keep agent memory consistent
<!-- \title{Ripple: Learned Dependency Links Keep Agent Memory Consistent} -->
Working outline for the conference paper (author: Omjee R Giri). Every number is a
macro (docs/paper/README.md); a refused macro reads "TBD (pending run)". Claims and
hypotheses are those of docs/00-vision.md and docs/04-evaluation.md; this outline
adds none. Status: the outline is the evidence map; the written draft is docs/paper/paper.md
(ADR-0136).

Legend for each section: **Supports** (claim or hypothesis ids), **Evidence** (macros
or figures), **Sources** (docs and ADRs the prose draws on).

## Abstract
<!-- \begin{abstract} ... \end{abstract} -->
- Problem: agents act on knowledge that went stale; current memory systems fix the
  contradicted fact and leave its dependents (docs/00 Problem).
- Idea: explicit dependency links; deterministic code picks WHICH memories a change
  affects, the LLM decides only HOW to fix each (docs/00 Thesis, ADR-0003).
- Results sentence, one neutral clause per hypothesis (the direction is whatever the
  numbers show): update accuracy at {{num:h1.accuracy_ratio}} of check-everything for
  {{num:h1.cost_ratio}} of its cost (H1); LLM-minus-trained linker F1 difference of
  {{num:h3.f1_difference_points}} points at {{num:h3.cost_ratio}} of the LLM's cost (H3);
  jobs-minus-finance F1 difference of {{num:h4.transfer_difference_points}} points for
  the trained linker (H4); a pilot with {{num:pilot.students}} students (C3).
- **Supports** C1–C4, H1–H4.

## Introduction
<!-- \section{Introduction}\label{sec:intro} -->
- The stale-belief failure, the CGPA example (docs/00 Problem).
- Positioning sentence from docs/06 (cascading invalidation exists; links were given by
  hand at small scale).
- Contributions as bullets, verbatim from docs/00: C1 learned dependency induction,
  C2 action-level evaluation, C3 real-world pilot, C4 cost.
- What we do not claim (docs/00): not the inventor of cascading invalidation, not a
  general assistant, no financial advice, the agent never applies for the user (I6).
- **Supports** C1–C4. **Sources** docs/00, docs/06.

## Related work
<!-- \section{Related Work}\label{sec:related} -->
- Cascading invalidation and repair: PACMI, rollback repair, MemTX (docs/06 table).
- Consistency as a property of agent memory: GEM.
- Temporal knowledge graphs: Zep/Graphiti (contradiction, not cascade) — baseline
  candidate.
- Benchmarks: STALE, RECON. Belief memory and judge gaps: Nous.
- **Supports** positioning of C1 and C2. **Sources** docs/06 (re-check arXiv monthly).

## Ripple: memory with dependencies
<!-- \section{Ripple}\label{sec:ripple} -->
### Data model
<!-- \subsection{Data Model}\label{sec:model} -->
- Memories as versioned rows; links copied to the new version (ADR-0014); link
  classes depends_on and snapshot_of (ADR-0013); validity states VALID, SUSPECT,
  PENDING_USER, RETIRED (docs/03).
- Every change is a memory write; temporary facts self-expire (ADR-0015).
### The ripple engine
<!-- \subsection{The Ripple Engine}\label{sec:engine} -->
- Wave-by-wave traversal over core link classes (ADR-0013); the graph decides scope,
  the LLM decides action (ADR-0003); rule-first resolution (ADR-0019).
- Invariants as design guarantees: I1 retrieval never returns RETIRED, I2 every
  change has a ChangeEvent, I3 no LLM in traversal, I4 schema-validated LLM output,
  I7 forget cascades (each with a named test).
- The engine body is the author's implementation (roadmap Phase 1, [human]).
### Asking the user
<!-- \subsection{Asking the User}\label{sec:ask} -->
- PENDING_USER and the answer flow; questions asked versus needed (ADR-0063).
- **Supports** the mechanism behind C2 and C4. **Sources** docs/02, docs/03, ADR-0003,
  ADR-0013–0015, ADR-0019.

## Learned dependency induction (C1)
<!-- \section{Learning Dependency Links}\label{sec:linker} -->
- Task: given a new memory and a candidate parent, predict the typed link or none.
- Data: labelled pairs (contract C5, bench/linkpairs.py) with provenance RULE,
  SCENARIO, LLM, HUMAN; split by persona and template (ADR-0061); leakage test
  (WS-14); hand-checked sample for agreement (ADR-0009, WS-14 protocol).
- Model: a small trained classifier (ADR-0009; training loop [human], roadmap Phase 4).
- Candidate pre-filter and its recall cap (proposal 0002).
- **Evidence** figure `linker_f1`; macros `link.rule.jobs_v0.f1`,
  `link.llm.jobs_v0.f1`, `link.trained.jobs_v0.f1` and their `usd_per_1k_pairs`.
- **Supports** C1, H3, H4. **Sources** ADR-0009, proposal 0002, WS-14 ADRs.

## RippleBench (C2)
<!-- \section{RippleBench}\label{sec:bench} -->
- Jobs track v0: seeded personas × seven template families, gold state for every
  memory after every event (ADR-0061).
- News track (real stories, curated by the author; synthetic until then) and finance
  track (test only, the unseen domain for H4) — WS-15.
- External: STALE adapter (WS-15; the format mapping is a docs/04 open question).
- Replay harness: per-event snapshots, recommendations with `based_on`, time to
  consistency and the stale-action window (ADR-0062, proposal 0003).
- Size of the jobs track, as replayed by the scripted-oracle sanity run:
  {{num:oracle.v0.check_everything.scenarios}} scenarios and
  {{num:oracle.v0.check_everything.checks}} gold checks (a manifest-based dataset macro is
  an open item).
- **Supports** C2. **Sources** ADR-0061, ADR-0062, docs/04 RippleBench.

## Experimental setup
<!-- \section{Experimental Setup}\label{sec:setup} -->
- Baselines (docs/04, ADR-0060): append-only, newest-wins, check-everything (LLM
  re-checks all memories), Mem0-style (open: real library or reimplementation).
- Same store, resolver and clock for every strategy; cost counted by one
  CountingResolver (ADR-0060). No call budget is imposed: check-everything's unbounded
  re-checks are the cost H1 measures against.
- Metrics (ADR-0063): update accuracy (H1's reading, proposed), stale kept, wrongful
  changes, questions asked, stale retrieval rate, stale recommendation rate, time to
  consistency, cost per ripple, tokens, USD.
- Protocol (docs/04): models pinned per run, three seeds minimum for headline numbers,
  LLM judge calibrated on a human-labelled sample, eval-auditor before publication. The
  registry has hand-check agreement macros (`handcheck.jobs_v0.*`) but no LLM-judge
  macros: no judge exists yet, and the paper reports none until one does.
- Headline numbers read the held-out split (ADR-0061 `test`); provisional until the
  Phase 3 baseline ADR.
- **Supports** fairness of every comparison. **Sources** ADR-0060, ADR-0063, docs/04.

## Results
<!-- \section{Results}\label{sec:results} -->
### Sanity: replaying the jobs track without an LLM
<!-- \subsection{Scripted-Oracle Replay}\label{sec:sanity} -->
- Scripted oracle resolver, zero LLM calls; measures write and ripple semantics only.
- Table `tab:sanity` (rows strategy; columns scenarios passed, pass share, checks
  failed, resolver calls):
  - append-only: {{num:oracle.v0.append_only.scenarios_passed}},
    {{num:oracle.v0.append_only.pass_share}}, {{num:oracle.v0.append_only.checks_failed}},
    {{num:oracle.v0.append_only.resolver_calls}}
  - newest-wins: {{num:oracle.v0.newest_wins.scenarios_passed}},
    {{num:oracle.v0.newest_wins.pass_share}}, {{num:oracle.v0.newest_wins.checks_failed}},
    {{num:oracle.v0.newest_wins.resolver_calls}}
  - check-everything: {{num:oracle.v0.check_everything.scenarios_passed}},
    {{num:oracle.v0.check_everything.pass_share}}, {{num:oracle.v0.check_everything.checks_failed}},
    {{num:oracle.v0.check_everything.resolver_calls}}
  - ripple: {{num:oracle.v0.ripple.scenarios_passed}}, {{num:oracle.v0.ripple.pass_share}},
    {{num:oracle.v0.ripple.checks_failed}}, {{num:oracle.v0.ripple.resolver_calls}}
- Figure `baselines_v0` (generated/figures/baselines_v0.*).
- Sanity check only; supports no claim (memory-state checks under an oracle, not
  action-level evidence).
### H1: accuracy against cost
<!-- \subsection{Accuracy and Cost (H1)}\label{sec:h1} -->
- Headline: {{num:h1.accuracy_ratio}} of check-everything's update accuracy at
  {{num:h1.cost_ratio}} of its cost per ripple. The H1 target is the one stated in
  docs/04; the outline does not restate it.
- Table `tab:h1` (rows strategy; columns update accuracy, stale kept, wrongful
  changes, cost per ripple, tokens per ripple, USD per ripple):
  - ripple: {{num:mem.ripple.update_accuracy}}, {{num:mem.ripple.stale_kept}},
    {{num:mem.ripple.wrongful_changes}}, {{num:mem.ripple.cost_per_ripple}},
    {{num:mem.ripple.tokens_per_ripple}}, {{num:mem.ripple.usd_per_ripple}}
  - check-everything: {{num:mem.check_everything.update_accuracy}},
    {{num:mem.check_everything.stale_kept}}, {{num:mem.check_everything.wrongful_changes}},
    {{num:mem.check_everything.cost_per_ripple}},
    {{num:mem.check_everything.tokens_per_ripple}},
    {{num:mem.check_everything.usd_per_ripple}}
  - newest-wins: {{num:mem.newest_wins.update_accuracy}},
    {{num:mem.newest_wins.stale_kept}}, {{num:mem.newest_wins.wrongful_changes}},
    {{num:mem.newest_wins.cost_per_ripple}}
  - append-only: {{num:mem.append_only.update_accuracy}},
    {{num:mem.append_only.stale_kept}}, {{num:mem.append_only.wrongful_changes}},
    {{num:mem.append_only.cost_per_ripple}}
- Figure `h1_accuracy_cost`.
- **Supports** H1, C4, Q1, Q3.
### H2: stale retrieval
<!-- \subsection{Stale Retrieval (H2)}\label{sec:h2} -->
- Ripple {{num:mem.ripple.stale_retrieval_rate}} against append-only
  {{num:mem.append_only.stale_retrieval_rate}}; difference
  {{num:h2.stale_retrieval_gap_points}} points. "Far below" has no numeric target yet,
  and "standard memory retrieval" may mean a Mem0-style baseline rather than append-only
  (docs/04 Open; provisional comparator).
- **Supports** H2.
### Action level: stale recommendations and time to consistency (C2)
<!-- \subsection{Action-Level Effects}\label{sec:actions} -->
- Stale recommendation rate: ripple {{num:mem.ripple.stale_recommendation_rate}},
  check-everything {{num:mem.check_everything.stale_recommendation_rate}}, newest-wins
  {{num:mem.newest_wins.stale_recommendation_rate}}, append-only
  {{num:mem.append_only.stale_recommendation_rate}}.
- Never-converged share: ripple {{num:mem.ripple.ttc_share_never_converged}},
  newest-wins {{num:mem.newest_wins.ttc_share_never_converged}}, append-only
  {{num:mem.append_only.ttc_share_never_converged}}.
- Questions asked: ripple {{num:mem.ripple.questions_asked}} (needed versus asked is
  derived in the report, ADR-0063).
- **Supports** C2, Q2.
### H3 and H4: the link finder
<!-- \subsection{Link Finder (H3, H4)}\label{sec:h3h4} -->
- H3: trained F1 {{num:link.trained.jobs_v0.f1}} against LLM
  {{num:link.llm.jobs_v0.f1}} (LLM minus trained: {{num:h3.f1_difference_points}}
  points) at {{num:h3.cost_ratio}} of the LLM's cost per thousand pairs; rule linker on
  scenario-labelled pairs {{num:link.rule.jobs_v0.f1_scenario}} as the floor (its
  overall F1 includes pairs labelled by its own rules). Typed F1
  ({{num:link.trained.jobs_v0.typed_f1}}) and the strict split
  ({{num:link.trained.jobs_v0.f1_strict}}) beside it; untyped F1 on silver labels is the
  provisional H3 reading. Silver-label quality: hand-check agreement
  {{num:handcheck.jobs_v0.agreement}}, kappa {{num:handcheck.jobs_v0.kappa}}.
- H4: trained F1 on finance {{num:link.trained.finance_v1.f1}}; jobs minus finance
  {{num:h4.transfer_difference_points}} points ("modest" has no numeric target yet, docs/04
  Open). LLM linker on finance {{num:link.llm.finance_v1.f1}} for reference.
- Figure `linker_f1`.
- **Supports** C1, H3, H4, Q4.
### Ablations
<!-- \subsection{Ablations}\label{sec:ablations} -->
- Table `tab:ablations` (rows ablation; columns update accuracy, stale recommendation
  rate, cost per ripple), against full ripple in `tab:h1`:
  - without graph: {{num:ablation.no_graph.update_accuracy}},
    {{num:ablation.no_graph.stale_recommendation_rate}},
    {{num:ablation.no_graph.cost_per_ripple}}
  - LLM linker instead of trained: {{num:ablation.llm_linker.update_accuracy}},
    {{num:ablation.llm_linker.stale_recommendation_rate}},
    {{num:ablation.llm_linker.cost_per_ripple}}
  - without Curator: {{num:ablation.no_curator.update_accuracy}},
    {{num:ablation.no_curator.stale_recommendation_rate}},
    {{num:ablation.no_curator.cost_per_ripple}}
  - without evidence retrieval: {{num:ablation.no_evidence.update_accuracy}},
    {{num:ablation.no_evidence.stale_recommendation_rate}},
    {{num:ablation.no_evidence.cost_per_ripple}}
  - without ask-user: {{num:ablation.no_ask_user.update_accuracy}},
    {{num:ablation.no_ask_user.stale_recommendation_rate}},
    {{num:ablation.no_ask_user.cost_per_ripple}}
- **Supports** attribution of H1 and C2 effects to components. bench.run runs the two
  offline ablations (`--ablation no_graph|no_ask_user`, ADR-0122); their oracle readings
  are the `oracle_ablation.*` macros (ADR-0135). The others need a model.

## Pilot deployment (C3)
<!-- \section{Pilot Deployment}\label{sec:pilot} -->
- Setting: placement season, consenting students (docs/pilot, NFR-3), the agent never
  applies (I6), allowed sources only (ADR-0008).
- Pilot metrics (docs/04): {{num:pilot.students}} students;
  saved or applied share {{num:pilot.saved_or_applied_share}}; days earlier than
  self-discovery {{num:pilot.days_earlier_than_self_discovery}}; stale recommendation
  rate {{num:pilot.stale_recommendation_rate}}; question usefulness
  {{num:pilot.question_usefulness_share}}; self-reported trust {{num:pilot.trust_score}}.
- **Supports** C3. **Sources** docs/pilot, WS-16 weekly report, ADR-0008.

## Cost (C4)
<!-- \section{Cost}\label{sec:cost} -->
- Graph-scoped resolution against re-checking everything: cost per ripple, tokens and
  USD per ripple from `tab:h1`; prices only from config (I8, config/llm.default.toml).
- **Supports** C4, H1. **Evidence** `mem.*.cost_per_ripple`, `mem.*.usd_per_ripple`.

## Limitations and threats to validity
<!-- \section{Limitations}\label{sec:limits} -->
- Synthetic jobs and finance data until curated; news stories need the author's
  curation (docs/04).
- Scripted-oracle replay measures semantics, not language understanding.
- The bench action layer is a placeholder ranking (ADR-0062) until the real ranking
  replaces it.
- One placement season, one institution; self-selection of pilot students.
- LLM-judge scores reported beside automatic metrics and a human-checked sample
  (docs/04 Protocol).

## Ethics
<!-- \section{Ethics}\label{sec:ethics} -->
- Consent and data handling (docs/pilot), forget API (I7), no submissions for the user
  (I6), no financial advice (docs/00).

## Conclusion
<!-- \section{Conclusion}\label{sec:conclusion} -->
- One paragraph per claim, each answered with its macros whether it holds or not
  (docs/00 Success).

## Reproducibility appendix
<!-- \appendix\section{Reproducibility}\label{sec:repro} -->
- Every number: generated/numbers.json names the results/ folders, git sha, seeds,
  models and prompt versions behind it.
- Camera-ready gate: `uv run python -m paper.numbers --strict` exits non-zero while any
  macro is refused; the I8 test (tests/paper) fails on any untraced number in docs.
