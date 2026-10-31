# Ripple: graph-scoped consistency for agent memory, and how far a small model gets at learning the graph
<!-- \title{Ripple: Graph-Scoped Consistency for Agent Memory} -->
Workshop-length draft (author: Omjee R Giri; drafted with the collaborator on
2026-10-31). Every number is a macro (`{{num:<key>}}`, ADR-0110, ADR-0136). The copy
with values filled in is docs/paper/generated/draft/paper.md, written by
`uv run python -m paper.numbers --draft` from results/. The tree is uncommitted, so
every value is a DRAFT value (ADR-0135); a camera-ready version needs the first commit,
a re-run, and `paper.numbers --strict`. The section map and evidence plan are in
docs/paper/paper-outline.md.

## Abstract
<!-- \begin{abstract} -->
Agents that remember for months fail less by forgetting than by acting on beliefs whose
premises have changed. When a student's grade rises, an eligibility verdict, a
recommendation and a search filter that were derived from the old grade must change
too; memory systems that resolve contradictions fix the fact and leave its dependents
stale. Ripple makes dependencies between memories explicit links. A deterministic wave
engine decides *which* memories a change can affect; a resolver (rules first, then an
LLM) decides only *how* to fix each one, one wave at a time, and every change leaves an
audited event. We describe the model, its invariants and a working job-hunt agent built
on it, and evaluate it on RippleBench, three generated tracks (jobs, news, finance) with
the gold state of every memory after every event. With a scripted oracle resolver and
gold links, which isolates the engine's semantics, Ripple reaches
{{num:oracle_h1.v0.accuracy_ratio}} of a check-everything baseline's update accuracy at
{{num:oracle_h1.v0.cost_ratio}} of its resolver calls on the jobs test split. The
accuracy half of our first hypothesis holds by construction under the oracle; the cost
half misses its target on these small stores. Superseded and suspect beliefs never reach
retrieval unflagged, while an append-only memory returns unflagged stale results
({{num:oracle_mem.v0.append_only.stale_retrieval_rate}} of probe results). A fine-tuned
ModernBERT-base link finder scores {{num:link.trained.jobs_v0.f1_both}} F1 on jobs pairs
from unseen personas and templates, against {{num:link.rule.jobs_v0.f1_both}} for a rule
linker, a difference within seed noise, and it does not transfer to the finance domain
({{num:link.trained.finance_v1.f1}} F1). The LLM-linker comparison, LLM costs and a
student pilot are pending; the benchmarks are synthetic.
<!-- \end{abstract} -->

## Introduction
<!-- \section{Introduction}\label{sec:intro} -->
A long-running agent accumulates beliefs, and most of them are not observations but
conclusions: this opening suits the student, that deadline needs a reminder, these are
the filters to search with. Each conclusion was right when it was drawn, and each rests
on facts that can change. When one does, the dangerous outcome is not that the agent
forgets the fact; it is that the agent keeps acting on conclusions that no longer
follow. Our running example comes from the product we built: a student's CGPA rises
above an employer's cutoff. The fact is easy to update. The eligibility verdict, the
"skip this one" recommendation and the search criteria built on the old value are not,
unless something knows they depended on it (docs/00-vision.md).

Ripple's thesis is a division of labour. Dependencies between memories are stored as
explicit, typed links. When a memory changes, deterministic code walks those links and
decides which memories could be affected; an LLM, or a domain rule before it, decides how
to fix each affected memory: keep it, update it, retire it, or ask the user (ADR-0003).
The walk proceeds wave by wave, and a "keep" stops its branch, so a change costs model
calls only as far as it actually propagates (ADR-0013).

The idea of propagating a change along recorded dependencies is old: truth maintenance
systems did it for justified beliefs, and recent agent-memory work applies cascading
invalidation to LLM memories (related work, below). What that recent work leaves open,
by its own account in the papers we track (docs/06-related-work.md), is where the links
come from: they are annotated by hand at small scale. Our contributions, as set out in
docs/00-vision.md, are:
- **C1, learned dependency induction:** a small trained model that infers typed links
  between memories from their text.
- **C2, action-level evaluation:** measuring whether a cascade changes what the agent
  shows and recommends, not only memory states.
- **C3, a real-world pilot:** a deployed job-hunt agent used by students in a placement
  season.
- **C4, cost:** graph-scoped resolution against re-checking every memory, measured.

This draft reports where each stands on 2026-10-31. The engine, the product and the
benchmark are built; the cost comparison (C4) and the action-level metrics (C2) are
measured with a scripted oracle; the learned link finder (C1) is trained and evaluated
against a rule baseline; the LLM-linker comparison, every LLM-cost number and the pilot
(C3) are pending. We say which hypotheses hold and which do not.

What we do not claim: we did not invent cascading invalidation; Ripple is not a general
personal assistant; finance is an unseen-domain test, never advice; and the agent never
applies to a job or acts on an external site for the student (invariant I6, ADR-0008).

## Problem
<!-- \section{Problem}\label{sec:problem} -->
A memory store holds facts (what the user said or a source stated) and derived beliefs
(what the agent concluded). A change event writes a new fact, a new version of a fact, or
the expiry of a temporary one. After the event, every derived belief is in one of three
conditions: still correct, in need of an update, or no longer supported. A store is
*consistent* after an event when every belief is in the state a careful human would put
it in given the new fact. Three properties make the problem hard in practice:
- **Hidden dependencies.** A recommendation depends on an eligibility verdict, which
  depends on a grade and a cutoff; the recommendation never mentions the grade.
- **Not every dependent changes.** A deadline moving does not change eligibility; a
  temporary unavailability should restore availability when it ends without touching
  permanent facts; a resume version sent with a past application must not change when a
  new resume is written.
- **Some changes need the user.** When the evidence does not settle a belief, the right
  action is a question, and the beliefs below it should be shown as unconfirmed until it
  is answered.

Two naive strategies bound the space. *Append-only* memory keeps every statement and lets
retrieval sort it out; *newest-wins* replaces the contradicted fact and nothing else. A
third, *check-everything*, re-examines every live memory after every change: it can be
accurate, but its cost grows with the store, and it re-decides beliefs that nothing
touched. Ripple aims at check-everything's accuracy at a fraction of its cost (H1),
with stale beliefs kept out of retrieval (H2), using links a small model can learn (H3)
and that transfer across domains (H4). The hypotheses and their targets are stated in
docs/04-evaluation.md before any result; we quote the targets in words: H1 asks for at
least nine tenths of check-everything's accuracy at under one fifth of its cost.

## The Ripple model
<!-- \section{Ripple}\label{sec:ripple} -->
### Memories, versions and links
<!-- \subsection{Data Model}\label{sec:model} -->
A memory is a row with a kind declared by its domain (fact, derived; the jobs domain adds
opening, application and criteria), text content, an optional structured triple
(subject, attribute, value), a validity status, a validity interval, a confidence, a
sensitivity, a source reference and its creator (docs/03-data-model.md). Every version
is its own row: an update writes a new row that points at the one it supersedes and
retires the old one (ADR-0014). A temporary fact ("busy with exams this month") is an
ordinary memory with an end date; nothing else marks it temporary, and a nightly sweep
retires it when the date passes, without an LLM (ADR-0015).

A link runs from a parent to a dependent: the dependent is the memory that would be wrong
if the parent changed. Links carry a domain type and one of two core *classes* with fixed
behaviour (ADR-0013):
- **depends_on** propagates a change, is copied to the new version on update, and
  cascades on forget;
- **snapshot_of** does not propagate, stays with the old version, and is removed (not
  cascaded) on forget. A past application "sent with resume v1" is a snapshot: a new
  resume must not rewrite history, and the copy rule makes that fall out.

When a memory is updated, its incoming depends_on links are copied to the new version, so
its dependents still follow it, and its outgoing links are re-pointed at each parent's
latest version, so a second change to a parent still reaches it even if the link finder
misses the link the second time (ADR-0014). Core knows only the two classes; each domain
adapter maps its link types onto them, and the write flow rejects an unmapped type before
anything reaches core.

Validity has four states. VALID memories are returned by retrieval; SUSPECT memories
(under review in an open ripple) and PENDING_USER memories (waiting for an answer) are
returned only with a flag; RETIRED memories never are (invariant I1). Hard deletion
happens only through a forget API that removes a whole version chain and cascades along
depends_on links (I7).

### The ripple: waves, resolution and commits
<!-- \subsection{The Ripple Engine}\label{sec:engine} -->
A ripple starts from a memory write. The write's transaction also opens a ChangeEvent,
so even a change with no dependents leaves history (I2). The engine is a pure iterator
over a snapshot of the dependency graph (docs/learning/ripple-engine.md):
- wave one is the depends_on dependents of the seed (the new version, or the retired
  memory for an expiry), with no status filter;
- the runner marks the wave SUSPECT and commits, so retrieval flags those beliefs at
  once;
- the resolver decides keep, update, retire or ask for each member, with the trigger, the
  belief and its parents as evidence; the decisions and state changes commit as one
  transaction appended to the ChangeEvent;
- only updated or retired memories seed the next wave: a keep halts its branch;
- an ask parks the memory in PENDING_USER and marks its depends_on subtree SUSPECT
  without resolving it; the answer later restores the subtree or starts a new ripple;
- a visited set makes cycles terminate and a depth limit reports truncation.

The engine never calls an LLM (I3); a boundary test forbids the import. Resolution is
rule-first (ADR-0019): a domain rule (the jobs eligibility rule compares a grade with a
cutoff) decides when it can, and returns nothing when a parent is missing or in doubt;
only then is the LLM resolver asked. Every LLM output is parsed into a Pydantic schema
before use, and invalid output is retried or rejected, never partially applied (I4).
Each wave is two commits, so a crash leaves memory at the last commit; the nightly sweep
resumes open ChangeEvents under a per-event lease (NFR-4, ADR-0099).

### Invariants
<!-- \subsection{Invariants}\label{sec:invariants} -->
The design guarantees are written as invariants, each with a named test
(`test_invariant_I<n>_...`): I1 validity-aware retrieval; I2 a ChangeEvent with reason and
evidence for every state change, whatever triggered it (a ripple, an expiry, a user edit
or a user answer); I3 no LLM in traversal; I4 schema-validated LLM output; I5 the agent
never invents profile facts, experience or numbers; I6 the agent never submits an
application or acts on an external site; I7 forget cascades over the whole version
chain; and I8, which governs this paper: every number in the docs or the paper traces to
a run folder in results/.

## The system
<!-- \section{System}\label{sec:system} -->
Ripple is a Python package with a domain-agnostic core (models, store protocol, engine,
the Linker and Resolver protocols), a PostgreSQL store with pgvector (SQLAlchemy and
Alembic, ADR-0016), an LLM router that is the only code calling a provider, a retrieval
layer, LangGraph agents and delivery surfaces (docs/02-architecture.md). The core imports
no ORM, framework or other ripple package.

**Intake.** A statement goes through change detection, deterministic for structured facts
and LLM-backed for prose, which turns "this month" into an end date (ADR-0020); then a
new memory or version is written; a linker proposes links; the ripple runs. Three linkers
sit behind one protocol: a rule linker (whole-word mentions of a structured fact's
attribute or value), an LLM linker, and the trained linker of the C1 section below,
chosen by configuration with the LLM linker as default until H3 is judged (ADR-0128).

**Retrieval.** Hybrid lexical and dense search (the dense model waits for its ADR;
lexical BM25 and Postgres full text today, ADR-0026), one hop of graph expansion that
skips history links, evidence references, and the one visibility rule of I1 applied last
(docs/learning/retrieval.md).

**The job-hunt agent.** A jobs adapter declares opening, eligibility, fit, reminder and
criteria beliefs and their link types, with rules that never guess. Resume and job
description parsers quote the span each field came from, and nothing enters memory until
the student confirms it (FR-1, FR-2). A conversation agent answers only from retrieved,
cited memories; a tailor suggests which of the student's real projects to highlight; a
Scout fetches openings only from an allowed-sources registry that respects robots and
terms (ADR-0008); a worker runs the nightly sweep, the digest and alerts. Students reach
it through a web dashboard with a memory inspector and a dependency map, a Telegram bot
and an MCP server. None of these surfaces has an "apply" action (I6).

## RippleBench
<!-- \section{RippleBench}\label{sec:bench} -->
RippleBench replays timelines of events against a memory strategy and checks the state
of every labelled memory after every event (ADR-0061, ADR-0062).
- **Jobs track (v0).** Generated from seeded personas and seven template families, one
  per gold behaviour: a changed fact whose dependents must follow, an unrelated change
  that must change nothing, a temporary fact that expires, a chain of dependencies, a
  belief the evidence cannot settle (an ask), a snapshot that must not move, and a
  forget that must cascade (docs/learning/bench-v1.md).
  The checked-in seed has {{num:oracle.v0.check_everything.scenarios}} scenarios and
  {{num:oracle.v0.check_everything.checks}} gold checks.
- **News and finance tracks (v1).** The same seven families in two other vocabularies:
  stories that are revised or retracted and the summaries built on them, and investment
  theses whose assumptions break (ADR-0101). Finance is test only, the unseen domain for
  H4 (ADR-0102). Both are synthetic until the author curates real stories.
- **Splits.** Train and test are split by persona and template, never by item. The test
  split holds the persona and template cells no link-finder training pair may come from;
  the engine and the baselines were not trained on anything.
- **Seeds.** Each track is generated with three generator seeds; the first reproduces the
  checked-in data, and each seed redraws its own split (ADR-0121). Headline numbers are
  means over the three seeds.
- **Action layer and probe.** After each event the harness records the recommendations a
  placeholder ranking would show, with the beliefs each was based on, and queries the
  real hybrid retriever once per gold memory with that memory's first wording (the
  closest match for an outdated row; ADR-0120). Stale recommendations are measured on
  the jobs track only, since the placeholder ranks jobs openings.

**Metrics** (ADR-0063, ADR-0120, ADR-0123). *Update accuracy* is correct updates over
should-change targets; *dependent update accuracy* leaves out the memory the event wrote
itself, which every strategy gets right; *stale kept* and *wrongful changes* count
targets left untouched and targets moved that should have stayed, per scenario;
*questions asked* counts asks; *stale retrieval rate* is the share of probe results that
are unflagged and gold-stale; *stale recommendation rate* is the share of shown
recommendations resting on a stale belief; the *never-consistent share* is the share of
should-change targets that never reached gold (time to consistency); *cost per ripple*
is resolver calls per ChangeEvent, the calls an LLM resolver would have made. Rates pool
counts over scenarios before dividing.

## Baselines and protocol
<!-- \section{Experimental Setup}\label{sec:setup} -->
Four strategies share one store, one resolver, one clock and one counting wrapper around
the resolver (ADR-0060): **append-only** (every statement stays valid), **newest-wins**
(the contradicted fact is retired, nothing else), **check-everything** (after each write,
every VALID memory is re-resolved in one wave, applied parents first, ADR-0104) and
**ripple**. A Mem0-style baseline is not built yet (whether it should be the real library
or a reimplementation is open in docs/04-evaluation.md).

All runs in this draft use the **scripted oracle resolver**: it answers from the scenario
file, so no LLM is called and tokens and dollars are not measured. Links come from the
scenario file (gold links), not from a link finder. The oracle and gold links remove
language understanding from the comparison on purpose: what remains is whether each
strategy's *scope*, which memories it re-examines, reaches the right ones and at what
cost. Two ablations run offline: ripple without the graph (check-everything's scope under
the ripple name) and ripple without asking the user (every ask becomes a keep)
(ADR-0122). The model-backed ablations (LLM linker instead of the trained one, without
the Curator, without evidence retrieval) need a provider key.

The protocol follows docs/04-evaluation.md: one results/ folder per run with its
configuration, seeds, models and prompt versions; three seeds for headline numbers; and
an eval-auditor review before any number is published. No LLM judge exists yet, so there
is nothing to calibrate.

## Results
<!-- \section{Results}\label{sec:results} -->
Every value below is a seed mean read from the run folders listed beside it in
docs/paper/generated/draft/numbers.md; the summary report
results/2026-10-31_benchsummary_uncommitted gives the same means with per-seed ranges.
The system-level macros, which need a link finder in the loop and an LLM resolver, are
shown beside the oracle readings and print "TBD (pending run)" until those runs exist.

### Sanity: the checked-in jobs data replayed by the oracle
<!-- \subsection{Scripted-Oracle Replay}\label{sec:sanity} -->
On the checked-in jobs data (all scenarios, one seed), ripple passes
{{num:oracle.v0.ripple.scenarios_passed}} of {{num:oracle.v0.ripple.scenarios}}
scenarios ({{num:oracle.v0.ripple.pass_share}}) with {{num:oracle.v0.ripple.checks_failed}}
failed gold checks and {{num:oracle.v0.ripple.resolver_calls}} resolver calls.
Check-everything passes {{num:oracle.v0.check_everything.scenarios_passed}}
({{num:oracle.v0.check_everything.pass_share}}), failing
{{num:oracle.v0.check_everything.checks_failed}} checks with
{{num:oracle.v0.check_everything.resolver_calls}} resolver calls. Newest-wins passes
{{num:oracle.v0.newest_wins.scenarios_passed}} with
{{num:oracle.v0.newest_wins.checks_failed}} failed checks, and append-only
{{num:oracle.v0.append_only.scenarios_passed}} with
{{num:oracle.v0.append_only.checks_failed}}. The hand-written smoke suite of the core
(tests/scenarios) passes {{num:smoke.ripple.scenarios_passed}} of
{{num:smoke.ripple.scenarios}} under ripple. This is a correctness check of the engine
against the specified semantics, not a discovery: the gold states and the oracle's
answers were written for graph-scoped propagation.

### H1: accuracy against cost
<!-- \subsection{Accuracy and Cost (H1)}\label{sec:h1} -->
On the jobs test split, mean over three generator seeds:

| strategy | update accuracy | dependent update accuracy | stale kept | wrongful changes | resolver calls per ripple |
|---|---|---|---|---|---|
| ripple | {{num:oracle_mem.v0.ripple.update_accuracy}} | {{num:oracle_mem.v0.ripple.dependent_update_accuracy}} | {{num:oracle_mem.v0.ripple.stale_kept}} | {{num:oracle_mem.v0.ripple.wrongful_changes}} | {{num:oracle_mem.v0.ripple.cost_per_ripple}} |
| check-everything | {{num:oracle_mem.v0.check_everything.update_accuracy}} | {{num:oracle_mem.v0.check_everything.dependent_update_accuracy}} | {{num:oracle_mem.v0.check_everything.stale_kept}} | {{num:oracle_mem.v0.check_everything.wrongful_changes}} | {{num:oracle_mem.v0.check_everything.cost_per_ripple}} |
| newest-wins | {{num:oracle_mem.v0.newest_wins.update_accuracy}} | {{num:oracle_mem.v0.newest_wins.dependent_update_accuracy}} | {{num:oracle_mem.v0.newest_wins.stale_kept}} | {{num:oracle_mem.v0.newest_wins.wrongful_changes}} | {{num:oracle_mem.v0.newest_wins.cost_per_ripple}} |
| append-only | {{num:oracle_mem.v0.append_only.update_accuracy}} | {{num:oracle_mem.v0.append_only.dependent_update_accuracy}} | {{num:oracle_mem.v0.append_only.stale_kept}} | {{num:oracle_mem.v0.append_only.wrongful_changes}} | {{num:oracle_mem.v0.append_only.cost_per_ripple}} |

Ripple reaches {{num:oracle_h1.v0.accuracy_ratio}} of check-everything's update accuracy
at {{num:oracle_h1.v0.cost_ratio}} of its resolver calls per ripple. The pattern repeats
on the other tracks: {{num:oracle_h1.news_v1.accuracy_ratio}} at
{{num:oracle_h1.news_v1.cost_ratio}} on news and {{num:oracle_h1.finance_v1.accuracy_ratio}}
at {{num:oracle_h1.finance_v1.cost_ratio}} on finance. The tracks mirror each other
family by family, so they show the semantics carry across vocabularies, not independent
evidence.

*The accuracy half is met by construction.* Under the oracle, ripple meets gold, so the
ratio cannot fall below one. Check-everything loses accuracy only in the ask family: its
single wave re-decides the asked belief's dependent on its own and leaves it VALID, where
gold wants it SUSPECT until the user answers. That outcome follows from the wave order
ADR-0104 chose (parents first); the other order would let check-everything pass the
family. The excess above one is that convention, not a measured advantage.

*The cost half is not met.* The target is under one fifth of check-everything's cost; on
these scenarios ripple uses {{num:oracle_h1.v0.cost_ratio}}. Both strategies open the same
number of ChangeEvents, so the ratio is a ratio of resolver calls
(on average {{num:oracle_mem.v0.ripple.resolver_calls}} against
{{num:oracle_mem.v0.check_everything.resolver_calls}} per run). The scenario stores are
small, since each scenario declares all its memories, so re-checking everything costs
only a small multiple of the graph-scoped ripple. That the ratio falls as stores grow is a
prediction we have not tested; the measurement H1 needs is the same scenarios padded with
unrelated memories at several store sizes.

*The no-graph ablation confirms where the saving comes from.* Ripple without its graph
scope reaches {{num:oracle_ablation.v0.no_graph.update_accuracy}} update accuracy at
{{num:oracle_ablation.v0.no_graph.cost_per_ripple}} resolver calls per ripple, the same
as check-everything, because it is check-everything's scope.

The system-level reading, with the trained linker and an LLM resolver, is
{{num:h1.accuracy_ratio}} of the accuracy at {{num:h1.cost_ratio}} of the cost; tokens and
dollars per ripple ({{num:mem.ripple.tokens_per_ripple}},
{{num:mem.ripple.usd_per_ripple}}) need a provider.

### H2: stale retrieval
<!-- \subsection{Stale Retrieval (H2)}\label{sec:h2} -->
On the jobs test split, {{num:oracle_mem.v0.append_only.stale_retrieval_rate}} of the
results append-only retrieval returns are unflagged stale beliefs; newest-wins returns
{{num:oracle_mem.v0.newest_wins.stale_retrieval_rate}}, check-everything
{{num:oracle_mem.v0.check_everything.stale_retrieval_rate}} and ripple
{{num:oracle_mem.v0.ripple.stale_retrieval_rate}}. The gap between append-only and ripple
is {{num:oracle_h2.v0.stale_retrieval_gap_points}} points on jobs,
{{num:oracle_h2.news_v1.stale_retrieval_gap_points}} on news and
{{num:oracle_h2.finance_v1.stale_retrieval_gap_points}} on finance. The mechanism is the
model, not tuning: superseded versions are RETIRED and never retrievable (I1), beliefs
waiting on a question are shown flagged, and flagged results do not count as stale.
Newest-wins retires only the direct fact, so its stale dependents stay visible.

H2 holds in direction. Whether the gap is "far below" waits for a numeric target, and
whether "standard memory retrieval" should mean a Mem0-style system rather than
append-only is open (docs/04-evaluation.md). The probe is close to the worst case for
strategies that keep old rows (it queries each memory with its first wording) and counts
every match rather than a top few. Ripple's zero rests on gold links and an oracle that
writes exactly the gold content: a link the finder misses, or an LLM update with the
wrong content, would show up here. The system-level gap is
{{num:h2.stale_retrieval_gap_points}} points.

### Action level: what the agent would show (C2)
<!-- \subsection{Action-Level Effects}\label{sec:actions} -->
With the placeholder ranking on the jobs test split, the share of shown recommendations
resting on a stale belief is {{num:oracle_mem.v0.ripple.stale_recommendation_rate}} for
ripple, {{num:oracle_mem.v0.check_everything.stale_recommendation_rate}} for
check-everything, {{num:oracle_mem.v0.newest_wins.stale_recommendation_rate}} for
newest-wins and {{num:oracle_mem.v0.append_only.stale_recommendation_rate}} for
append-only. The share of should-change targets that never reached gold is
{{num:oracle_mem.v0.ripple.ttc_share_never_converged}},
{{num:oracle_mem.v0.check_everything.ttc_share_never_converged}},
{{num:oracle_mem.v0.newest_wins.ttc_share_never_converged}} and
{{num:oracle_mem.v0.append_only.ttc_share_never_converged}} respectively. Ripple asks
{{num:oracle_mem.v0.ripple.questions_asked}} questions per scenario on average. Without
asking, ripple's update accuracy falls to {{num:oracle_ablation.v0.no_ask_user.update_accuracy}}:
the ask family is exactly where a belief cannot be settled without the student. The
recommendation sample is small (the counts per run are in
results/2026-10-31_benchsummary_uncommitted) and the ranking is a placeholder, so C2 is
demonstrated as a measurement here; its realistic-scale form is the pilot.

### H3 and H4: learning the links
<!-- \subsection{Link Finder (H3, H4)}\label{sec:h3h4} -->
**Task and data.** Given a memory and a candidate parent, predict the link type or none.
Pairs are generated from the jobs scenario snapshots, with provenance from the scenario
file or from structure rules, three negatives per positive and every reversed link kept
as a negative, split by persona and template like the bench (ADR-0090, ADR-0091). Only
test pairs identical to a training pair are removed, so many test pairs still share one
memory text with training (counted in training/data/jobs_v0_pairs.manifest.json). The jobs test split has
{{num:link.rule.jobs_v0.test_pairs}} pairs, of which
{{num:link.rule.jobs_v0.test_pairs_both}} come from personas *and* templates unseen in
training (the held_out=both cell, the one we read); finance has
{{num:link.rule.finance_v1.test_pairs}} pairs, all held out by domain.

**Model.** ModernBERT-base fine-tuned end to end on CPU as a pair classifier over the jobs
label space, with class-weighted cross-entropy, epoch and threshold chosen on a
validation persona, three training seeds (ADR-0125, ADR-0126). It is served behind the
same Linker protocol as the others.

**Jobs.** On the held_out=both cell the trained linker scores
{{num:link.trained.jobs_v0.f1_both}} F1 (precision
{{num:link.trained.jobs_v0.precision_both}}, recall {{num:link.trained.jobs_v0.recall_both}},
typed F1 {{num:link.trained.jobs_v0.typed_f1_both}}) against the rule linker's
{{num:link.rule.jobs_v0.f1_both}} (precision {{num:link.rule.jobs_v0.precision_both}},
recall {{num:link.rule.jobs_v0.recall_both}}). The difference,
{{num:link.jobs_v0.f1_both_trained_minus_rule_points}} points, is within the spread of
the three seeds (results/2026-10-31_linkpairs_summary_uncommitted): one seed is below
the rule linker, one level with it, one above. On unseen personas with seen templates
the trained linker is far ahead ({{num:link.trained.jobs_v0.f1_persona}} against
{{num:link.rule.jobs_v0.f1_persona}}), which says the model learned the templates'
wording, not that it induces dependencies in general. The cell rests on a small number
of gold links, so one prediction more or less moves its recall visibly.

**Finance transfer (H4).** Trained on jobs and scored on finance, the trained linker
scores {{num:link.trained.finance_v1.f1}} F1 (recall {{num:link.trained.finance_v1.recall}})
against the rule linker's {{num:link.rule.finance_v1.f1}}; the drop from the jobs cell
is {{num:h4.transfer_difference_points}} points, and the trained linker trails the rules
on finance by {{num:h4.finance_trained_minus_rule_points}} points. Most finance link
types do not exist in the jobs label space, and the model made almost no positive
predictions; the few it got right are of a type the two domains share
(results/2026-10-31_linkpairs_finance_v1_trained_uncommitted_3). **H4 is not supported on
this evidence.** "Modest drop" has no numeric target, but a fall to near zero, below a
rule linker on the same file, is not modest under any reading. These runs do not
separate the causes: a label space that does not cover finance, wording memorised from
one domain's templates, and too little data.

**H3 (pending).** H3 compares the trained linker with an LLM linker. There is no valid
provider key on the machine that produced these runs, so the LLM linker's F1
({{num:link.llm.jobs_v0.f1}}), the difference ({{num:h3.f1_difference_points}} points)
and the cost ratio ({{num:h3.cost_ratio}}) are pending; the commands that produce them
are in docs/results/link-finder.md. On cost, the trained linker takes
{{num:link.trained.jobs_v0.cpu_seconds_per_call}} CPU seconds per scored pair on the
machine used (process CPU time over all threads), against
{{num:link.rule.jobs_v0.cpu_seconds_per_call}} for the rules.

**Label quality.** All labels are silver: written by one author through the scenario
generators and structure rules. The stratified hand check of link pairs (ADR-0092) is the
author's to do; its agreement ({{num:handcheck.jobs_v0.agreement}}, kappa
{{num:handcheck.jobs_v0.kappa}}) is pending, and no link-finder number should be quoted
outside this draft before it exists.

## Limitations
<!-- \section{Limitations}\label{sec:limits} -->
- **Synthetic benchmarks.** All three tracks are generated from templates with invented
  people, companies and stories. They test consistency under labelled semantics, not
  language understanding, and the v1 tracks mirror v0 by construction.
- **Oracle resolver and gold links.** The memory results isolate the engine's scope.
  They say nothing yet about an LLM resolver's mistakes or a link finder's misses, which
  is where Ripple's real errors will come from.
- **No human audit of gold.** The expected states were written by the template authors;
  no sample has been hand-checked against them.
- **Design informed by the benchmark.** Decisions such as the wave order of ADR-0104 were
  made with these tracks' outcomes in view.
- **H1's cost half is not met** on small stores, and the scaling run is not done.
- **The link finder is weak where it matters.** It is not distinguishable from rules on
  fully held-out jobs pairs and fails on finance; C1, as stated, is not yet supported.
- **Pending pieces.** H3, every token and dollar figure, the model-backed ablations, the
  hand check, the Mem0-style baseline, the external STALE benchmark (its format mapping
  is open) and the pilot (C3).
- **Uncommitted code.** Every run here comes from an uncommitted tree; the numbers are
  draft values until the first commit and a re-run.

## Related work
<!-- \section{Related Work}\label{sec:related} -->
**Truth maintenance and belief revision.** Doyle's truth maintenance system (TMS;
*Artificial Intelligence*, 1979) records the justifications of beliefs and withdraws
beliefs whose support is retracted; de Kleer's assumption-based TMS (ATMS; *Artificial
Intelligence*, 1986) tracks the assumption sets under which each belief holds. Ripple's
depends_on links play the role of justifications, with two differences: the links are
proposed by a learned or prompted model rather than produced by an inference engine, and
the repair of a dependent is a decision (keep, update, retire, ask) rather than a logical
consequence. The AGM theory of belief revision (Alchourrón, Gärdenfors and Makinson,
*Journal of Symbolic Logic*, 1985) gives postulates for rational revision of a belief
set; Ripple's minimal-change behaviour (a keep halts a branch, an unrelated change
touches nothing) is in the spirit of those postulates, but we prove no AGM property.

**Memory for LLM agents.** MemGPT (Packer et al., 2023; now developed as Letta) manages
an agent's context like an operating system manages memory tiers. Mem0 (Chhikara et al.,
arXiv, 2025)  extracts and updates salient memories with add, update and
delete operations decided per new fact. A-MEM (Xu et al., 2025) organises memories as
linked notes that evolve when new ones arrive. Zep and its Graphiti engine (Rasmussen et
al., 2025) keep a bi-temporal knowledge graph and invalidate edges a new fact
contradicts. These systems update what a new fact contradicts or resembles; Ripple
updates what *depends* on it, including beliefs that never mention it, and audits every
change. Zep is a baseline candidate (docs/06-related-work.md).

**Cascading invalidation in agent memory.** docs/06-related-work.md (checked 2026-10-19)
tracks recent preprints that propagate invalidation through memory provenance or
dependency graphs and repair dependents: PACMI, a rollback-repair method, MemTX
(transactional belief commits), a position paper on dependency consistency for agent
memory (GEM), and the STALE and RECON benchmarks of implicit conflicts and cascades. We
take their framing as prior work and do not claim the idea; by those papers' own
descriptions as summarised there, the dependency links are given by annotation at small
scale, which is the gap C1 addresses. Their exact authorship and venues are to be
verified before submission.

**Knowledge editing.** ROME (Meng et al., NeurIPS 2022) and MEMIT (Meng et al., ICLR
2023) edit factual associations inside a model's weights; MQuAKE (Zhong et al., EMNLP
2023) shows that edited models often fail multi-hop questions whose answers should change
with the edited fact, and RippleEdits (Cohen et al., *TACL*, 2024)
evaluates exactly these "ripple effects" of an edit on related facts. That failure inside
parameters is the one Ripple addresses outside them, in an explicit memory where
dependents can be found and audited; the shared name is a coincidence of metaphor, and
RippleBench is unrelated to RippleEdits.

**Retrieval and staleness.** Retrieval-augmented generation (Lewis et al., NeurIPS 2020)
grounds answers in retrieved text, and later work on fresh and time-sensitive question
answering (for example FreshLLMs, Vu et al., Findings of ACL, 2024) shows that
retrieved knowledge goes out of date. Ripple's retrieval is validity-aware: a superseded
or retired belief is never returned, and a belief under review is returned only with a
flag (I1).

## Conclusion
<!-- \section{Conclusion}\label{sec:conclusion} -->
Ripple's engine does what it was designed to do. With gold links and a scripted oracle,
graph-scoped propagation meets every gold state the benchmark specifies, keeps stale
beliefs out of retrieval, and uses {{num:oracle_h1.v0.cost_ratio}} of check-everything's
resolver calls. The cost target of H1 is not met on small stores, and its accuracy half
is met by construction, so the first hypothesis is answered only in part; H2 holds in
direction; H4 is not supported; H3, the costs in tokens and dollars, and the pilot are
pending. The weakest link is literally the link: a small model trained on one domain's
templates is not yet distinguishable from rules on fully held-out pairs and does not
transfer. The next experiments follow directly: a store-size scaling run for H1, the LLM
linker for H3, a label space and training data that span domains for H4, and the
placement-season pilot for C3.

## Reproducibility
<!-- \appendix\section{Reproducibility}\label{sec:repro} -->
- The benchmark grid: `uv run python -m bench.matrix`, then
  `uv run python -m bench.summary` (docs/results/benchmark.md).
- The link finder: `training.train` per seed, then `training.evaluate` with
  `--linker rule|trained` and `--transfer` for finance, then `training.summarize`
  (docs/results/link-finder.md).
- The numbers: `uv run python -m paper.numbers --draft` today;
  `uv run python -m paper.numbers --strict` after the first commit and a re-run is the
  camera-ready gate. generated/numbers.json names, for every value, the results/ folders,
  seeds, models and prompt versions it came from.
- The I8 check: `uv run python -m paper.i8` and `uv run pytest tests/paper`.
