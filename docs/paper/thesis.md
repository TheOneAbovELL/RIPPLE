# Ripple: a consistency layer for agent memory
<!-- \documentclass{report} \title{Ripple: A Consistency Layer for Agent Memory} -->
B.Tech final-year project thesis, draft (author: Omjee R Giri; submission May 2028;
drafted with the collaborator on 2026-10-31). The chapter plan is
docs/paper/thesis-outline.md. Every number is a macro (`{{num:<key>}}`, ADR-0110,
ADR-0136); the copy with values filled in is docs/paper/generated/draft/thesis.md,
written by `uv run python -m paper.numbers --draft` from results/. The tree is
uncommitted, so every value is a DRAFT value (ADR-0135). Parts the author writes himself
(certificate, declaration, acknowledgements, the guide's name) are marked TODO(author).

## Front matter
<!-- \frontmatter -->
TODO(author): certificate, declaration, acknowledgements.

**Abstract.** Software agents that work for a person over months build up beliefs about
that person and the world, and most of those beliefs are conclusions drawn from other
beliefs. When a fact changes, the conclusions built on it go stale, and an agent that
keeps acting on them is confidently wrong. This thesis presents Ripple, a consistency
layer for agent memory. Dependencies between memories are stored as explicit, typed
links; when a memory changes, a deterministic wave engine finds the memories that could
be affected, and a resolver (domain rules first, then a language model) decides for each
whether to keep, update or retire it, or to ask the user. Every change is recorded with
its reason and evidence. On top of the layer we built a job-hunt agent for engineering
students: resume and job-description intake with confirmation, eligibility and fit
beliefs, a Scout over permitted sources, a web dashboard with a memory inspector and a
dependency map, a Telegram bot and an MCP server. We evaluate on RippleBench, three
generated benchmark tracks with the gold state of every memory after every event. With a
scripted oracle resolver and gold links, Ripple reaches
{{num:oracle_h1.v0.accuracy_ratio}} of a check-everything baseline's update accuracy at
{{num:oracle_h1.v0.cost_ratio}} of its resolver calls on the jobs test split, and never
returns a stale belief unflagged, where an append-only memory does in
{{num:oracle_mem.v0.append_only.stale_retrieval_rate}} of probe results. The cost target
of the first hypothesis is not met on these small stores, and its accuracy half holds by
construction under the oracle. A fine-tuned ModernBERT-base link finder scores
{{num:link.trained.jobs_v0.f1_both}} F1 on fully held-out jobs pairs against
{{num:link.rule.jobs_v0.f1_both}} for a rule linker, within seed noise, and does not
transfer to finance. The comparison with an LLM linker, all LLM costs and the student
pilot are pending.

**Abbreviations.** ADR, architecture decision record (docs/adr); C1 to C4, the claimed
contributions (docs/00-vision.md); H1 to H4, the hypotheses and Q1 to Q4, the evaluation
questions (docs/04-evaluation.md); I1 to I8, the invariants (CLAUDE.md); FR and NFR,
functional and non-functional requirements (docs/01-requirements.md); LLM, large language
model; MCP, Model Context Protocol; RAG, retrieval-augmented generation; TMS, truth
maintenance system; DPDP, India's Digital Personal Data Protection Act.

## Chapter: Introduction
<!-- \chapter{Introduction}\label{ch:intro} -->
### Motivation
Agents now remember and act for long periods: they keep notes about the user, track
tasks, watch sources and make suggestions. The failure that matters in such an agent is
not forgetting. It is acting, with confidence, on knowledge that has gone stale
(docs/00-vision.md). A concrete case from the domain this project serves: an engineering
student's CGPA rises above a company's cutoff. Updating the CGPA is trivial. But the
agent had also concluded "not eligible for this company", recommended skipping the
opening, and built search criteria around the old value. Unless something knows that
those conclusions depended on the CGPA, they survive the update, and the student is told
to skip an opening they now qualify for.

Memory systems for LLM agents handle the contradicted fact: they detect that a new
statement conflicts with an old one and replace it. The dependents are a different
problem. They rarely mention the fact they rest on, so neither similarity search nor
contradiction detection finds them.

### Problem statement and thesis
The problem this thesis addresses is keeping every belief in an agent's memory
consistent with the facts it rests on, at a cost that does not grow with the whole store
for every change, and in a way a user can inspect and correct.

The thesis of the project (docs/00-vision.md) is a division of labour: *make the
dependencies between memories explicit; deterministic code decides which memories a
change affects; the LLM decides only how to fix each one.* The graph bounds the scope of
every change, so the cost of a change follows how far it really propagates, and every
step is reproducible and auditable. The model is used where judgement is needed, on one
belief at a time, with the evidence in front of it.

### Objectives and research questions
The objectives are the four contributions of docs/00-vision.md:
- **C1** learned dependency induction: a small trained model that infers typed links
  between memories from their text, where recent cascading-invalidation work assumes the
  links are given;
- **C2** action-level evaluation: measuring whether cascades change what the agent
  recommends, not only memory states;
- **C3** a real-world pilot: the job-hunt agent used by students during a placement
  season;
- **C4** cost: graph-scoped resolution against re-checking everything, measured.

They are examined through four questions (docs/04-evaluation.md): Q1, does Ripple keep
memory correct after changes; Q2, does it stop the agent acting on stale knowledge; Q3,
at what cost compared with re-checking everything; Q4, can a small model infer the links,
and does it transfer to an unseen domain. The hypotheses H1 to H4, stated before any
result was produced, are given with the evaluation plan.

### Scope
| Role | Domain | Depth |
|---|---|---|
| Primary | Internship and job hunting | Full product and pilot |
| Secondary | News and current affairs | Benchmark only |
| Generalisation | Finance | Unseen-domain test only |

### What this work does not claim
It did not invent cascading invalidation (see the literature survey). The agent is not a
general personal assistant. Finance is used only as an unseen domain for testing link
transfer; nothing in the project gives financial advice. The agent never applies to a
job or acts on an external site for the student (I6, ADR-0008).

### Organisation
The literature survey places Ripple among agent-memory systems, truth maintenance, belief
revision and knowledge editing. The requirements chapter states what the system must do
and the evaluation plan written before any result. The design, engine, linking and
retrieval chapters describe the system; the product chapter describes the job-hunt agent
built on it. The benchmark and results chapters report the evaluation, followed by the
pilot plan, ethics and privacy, limitations, and conclusions.

## Chapter: Literature survey
<!-- \chapter{Literature Survey}\label{ch:literature} -->
### Truth maintenance and belief revision
The problem of withdrawing conclusions when their support changes was studied long
before LLMs. Doyle's truth maintenance system (*Artificial Intelligence*, 1979) attaches
justifications to beliefs and withdraws a belief when its justification is undermined.
De Kleer's assumption-based TMS (*Artificial Intelligence*, 1986) labels each belief with
the sets of assumptions under which it holds, so the consequences of many alternative
contexts can be tracked together. Both assume that justifications are produced by the
reasoner itself and that withdrawal is a logical consequence.

Belief revision theory, following Alchourrón, Gärdenfors and Makinson (*Journal of
Symbolic Logic*, 1985; the AGM theory), gives rationality postulates for revising a
belief set with new information, including minimal change. Ripple borrows two ideas in
spirit: dependencies are recorded explicitly, as justifications are, and an unrelated
change should change nothing. It differs in that its links are proposed by a learned or
prompted model from text, and the repair of a dependent is a decision (keep, update,
retire, ask) that may need judgement or the user. No AGM property is proved here.

### Memory for LLM agents
MemGPT (Packer et al., 2023), now developed as the Letta project, treats an LLM's context
as a small fast memory and manages paging to larger stores. Mem0 (Chhikara et al., arXiv, 2025)
 extracts salient facts from conversations and decides, per new fact,
whether to add, update or delete stored memories. A-MEM (Xu et al., 2025) organises
memories as linked notes in the manner of a Zettelkasten and lets new notes update
related ones. Zep (Rasmussen et al., 2025), built on the Graphiti engine, keeps a
bi-temporal knowledge graph and invalidates edges that a new fact contradicts. All four
handle what a new fact contradicts or resembles. A dependent belief that never mentions
the changed fact, such as a recommendation resting on an eligibility verdict that rests
on a grade, is outside what they find. Zep is the nearest system and a baseline
candidate (docs/06-related-work.md).

### Cascading invalidation in agent memory
docs/06-related-work.md (checked 2026-10-19, to be re-checked before submission) tracks a
group of recent preprints that bring cascading invalidation to LLM memories: PACMI
(provenance graphs with typed edges and cascading invalidation), a dependency-guided
rollback repair method, MemTX (transactional belief commits with typed cascading repair),
a position paper defining dependency consistency for agent memory (GEM), and two
benchmarks, STALE (implicit memory conflicts) and RECON (including cascade-propagation
questions). As summarised there, these works take the dependency links as given, by
annotation and at small scale, and report memory-state metrics. Their authorship and
venues are to be verified before this chapter is final; no number from them is quoted.

### Knowledge editing
Knowledge-editing methods change facts stored in a model's weights. ROME (Meng et al.,
NeurIPS 2022) locates and edits factual associations in a transformer's feed-forward
layers; MEMIT (Meng et al., ICLR 2023) scales this to many edits. MQuAKE (Zhong et al.,
EMNLP 2023) showed that edited models often fail multi-hop questions whose answers should
change with the edit, and RippleEdits (Cohen et al., *TACL*, 2024)
evaluates these "ripple effects" directly. The failure is the one this thesis addresses,
but inside parameters; Ripple works on an explicit memory, where dependents can be
found, repaired and audited. RippleBench, this project's benchmark, is unrelated to
RippleEdits despite the shared metaphor.

### Retrieval and staleness
Retrieval-augmented generation (Lewis et al., NeurIPS 2020) grounds a model's answers in
retrieved documents. Work on time-sensitive question answering (for example FreshLLMs,
Vu et al., Findings of ACL, 2024) shows that both model knowledge and retrieved
knowledge go out of date. Ripple's answer at the retrieval layer is validity-aware
search: superseded and retired beliefs are never returned, and beliefs under review are
returned with a flag (I1).

### The gap
Taken together: cascades are known to help, the links they need are assumed to be given,
the benchmarks are small, and evaluation stops at memory states. Ripple targets the
links (C1), evaluation at the level of actions (C2), deployment with real users (C3) and
the cost of scoping (C4). The positioning sentence of docs/06-related-work.md states it:
recent work showed cascading invalidation helps but assumed hand-annotated dependency
links at small scale; Ripple learns those links from raw memories and tests, in a
deployed agent, whether cascades change actions.

## Chapter: Requirements and evaluation plan
<!-- \chapter{Requirements}\label{ch:requirements} -->
### Functional requirements
The functional requirements and their acceptance criteria are in docs/01-requirements.md.
In summary:
- **FR-1 profile setup:** an uploaded resume is parsed into profile facts, and the
  student confirms each; no fact is stored without confirmation (I5).
- **FR-2 openings intake:** a pasted job description, a forwarded email or the Scout
  yields structured requirements (skills, CGPA cutoff, batch, deadline, location), each
  linked to the text span it came from.
- **FR-3 application tracking:** status per application, the resume version sent,
  follow-ups.
- **FR-4 derived beliefs:** eligibility, fit with cited job-description lines,
  reminders and search criteria, each linked to the memories it depends on.
- **FR-5 change detection:** contradictions are detected and classed as permanent or
  temporary; a temporary fact carries an end date and the nightly sweep retires it and
  ripples the expiry without an LLM.
- **FR-6 ripple:** traverse wave by wave, resolve keep, update, retire or ask per wave,
  stop a branch on keep, and write one ChangeEvent per ripple.
- **FR-7 ask the user** when confidence is low or sensitivity high; questions are
  queued and answers applied.
- **FR-8 Scout:** a daily schedule and a run on criteria change, permitted sources only,
  deduplication, ranking by eligibility, fit, urgency and variety.
- **FR-9 notifications:** a daily digest, and alerts for high-fit openings or deadlines
  within forty-eight hours.
- **FR-10 conversation** answers through validity-aware RAG with citations.
- **FR-11 tailor** suggests which real projects to highlight for an opening and never
  invents (I5).
- **FR-12 memory inspector:** see each belief, why it is held and its history; edit;
  forget (I7). An edit is a new version that ripples like any write.
- **FR-13 map dashboard:** openings, skills and applications as one live graph.
- **FR-14 MCP server:** search, save, update, forget, explain.
- **FR-15 export and delete** all of a user's data.
- **FR-16 link verification:** the nightly sweep re-checks weak links (added by the
  collaborator from the project proposal; for the author to confirm).

### Non-functional requirements
- **NFR-1** tests run fully offline, with no network and no real LLM.
- **NFR-2** cost and latency per ripple are logged per step; targets are set after the
  first baselines.
- **NFR-3** privacy: private storage, export and deletion on request, consent for the
  pilot, alignment with the DPDP Act.
- **NFR-4** reliability: provider fallback; a ripple wave is two atomic commits, so a
  failure leaves memory at the last commit and the sweep resumes the open event.
- **NFR-5** reproducibility: every evaluation run records its configuration, seeds,
  model and prompt versions, and commit.
- **NFR-6** observability: every agent step is traced with cost and latency.

### Invariants as testable requirements
Eight invariants turn the design's promises into tests, each named
`test_invariant_I<n>_...`:
- **I1** retrieval never returns RETIRED memories, and returns SUSPECT and PENDING_USER
  ones only with a flag;
- **I2** every memory state change writes a ChangeEvent with reason and evidence
  references, whatever its trigger kind (ripple, expiry, user edit, user answer);
- **I3** the ripple engine never calls an LLM;
- **I4** LLM output is parsed into a Pydantic schema before use, and invalid output is
  retried or rejected, never partially applied;
- **I5** the agent never invents profile facts, experience or numbers;
- **I6** the agent never submits an application or acts on an external site for the
  user;
- **I7** hard deletion happens only through the forget API, over the whole version chain
  and cascading along dependency links;
- **I8** every number in the README, the docs or this thesis traces to a file in
  results/.

### The evaluation plan, written first
ADR-0012 made the project evaluation-first: the questions, baselines, ablations, metrics,
hypotheses and protocol were written (docs/04-evaluation.md) before any engine code, so
that results could not shape the questions. The hypotheses, with their initial targets in
words, are:
- **H1** at least nine tenths of check-everything's accuracy at under one fifth of its
  cost;
- **H2** a stale retrieval rate far below standard memory retrieval;
- **H3** a trained linker within five points of an LLM linker at a fraction of the cost;
- **H4** the linker transfers to finance with a modest drop.
Several readings were left open until the first baselines, and each is recorded where it
was settled: H1's "accuracy" as update accuracy over should-change targets (ADR-0063),
H1's "cost" as resolver calls per ripple with tokens and dollars beside it, H2's
comparator as append-only memory, H3 and H4 as untyped F1 differences on silver labels
(the provisional readings of ADR-0110), and "three seeds" as three generator seeds (ADR-0121). "Far below"
and "modest" still have no numeric target.

The baselines are append-only, newest-wins, a Mem0-style memory and check-everything (an
LLM re-checks all memories). The ablations are: without the graph, an LLM linker instead
of the trained one, without the Curator, without evidence retrieval, and without asking
the user. The protocol requires pinned model versions, three seeds for headline numbers,
a calibrated LLM judge if one is used, and an independent audit before publication.

## Chapter: System design
<!-- \chapter{System Design}\label{ch:design} -->
### Principle and module boundaries
The architecture follows one principle: the graph decides scope; the LLM decides action
(ADR-0003). The core engine is domain-agnostic, and domains plug in through adapters
(docs/02-architecture.md).

| Module | Responsibility | May import |
|---|---|---|
| core | models, Store protocol, ripple engine, Linker and Resolver protocols, ChangeEvents | only core |
| linking | rule, LLM and trained linkers behind one protocol | core, llm |
| storage | SQLAlchemy tables, Alembic migrations, the Postgres store | core |
| retrieval | validity-aware hybrid search, graph expansion, evidence | core, storage |
| llm | provider router, schemas, versioned prompts; the only code calling a provider | core |
| agents | conversation and tailor graphs, the Scout loop | everything above |
| domains | one adapter per domain: schemas, link types, sources, rules | core, linking |
| api, mcp_server, notify, worker | delivery | everything |

Boundary tests enforce the import rules; in particular core imports no ORM, framework or
other ripple package, and nothing in core can reach an LLM client (I3).

### Data model
A **memory** is a row: identifier, user, domain, kind (declared by the domain adapter;
core interprets none), text content, an optional structured triple (subject, attribute,
value), status, validity interval, recording time, confidence, sensitivity, source
reference, creator, version and the identifier of the version it supersedes
(docs/03-data-model.md). Every version is its own row; an update writes a new row and
retires the old one (ADR-0014). A temporary fact is an ordinary memory with an end date
(ADR-0015).

A **link** runs from parent to dependent, with a domain link type, a core link class, a
strength (unused until an approved damping idea), the creator (rule, LLM, model or human),
a confidence, a creation time and a verification time. Two link classes have fixed
behaviour (ADR-0013):

| Class | Propagates a change | Copied to the new version | On forget of the parent |
|---|---|---|---|
| depends_on | yes | yes | dependent deleted (cascade) |
| snapshot_of | no | no | link removed, dependent kept |

The jobs domain maps eligibility, fit, reminder and criteria links, and the generic
fact and time-period links, to depends_on, and "sent with resume" to snapshot_of, so that
a new resume never rewrites a past application.

A **ChangeEvent** records each ripple: trigger kind (ripple, expiry, user edit, user
answer), trigger memory, affected memories, decisions (with wave number, action, reason,
evidence references, the new version and, for an ask, the question), the memories an ask
parked, cost, latency, a trace id and a completion time that stays empty while the ripple
is open. A **ForgetEvent** records a deletion by identifiers only.

Four **validity states** govern visibility: VALID (returned), SUSPECT and PENDING_USER
(returned only with a flag), RETIRED (never returned). The transitions are listed in
docs/03-data-model.md; for example SUSPECT becomes VALID on a keep, RETIRED on a retire
or an update, and PENDING_USER on an ask.

### Key decisions and their alternatives
Each significant decision has an ADR that lists the alternatives and why they lost
(docs/adr/README.md). The ones that shape the thesis:
- **ADR-0003, the graph decides scope:** rejected alternatives were LLM-only
  propagation (unbounded cost, no audit) and pure rules (cannot decide prose).
- **ADR-0004, PostgreSQL with pgvector and in-process traversal:** a graph database was
  rejected because per-user graphs are small and one store keeps transactions simple.
- **ADR-0007, retire, never silently delete:** history is kept for audit; deletion only
  through forget (I7).
- **ADR-0013, wave-by-wave ripple over two link classes:** full closure was rejected
  because it re-checks beliefs whose parent turned out unchanged.
- **ADR-0014, versions as rows with copied links:** a stable identity with mutable
  content was rejected because history and snapshots then need a second mechanism.
- **ADR-0010, a provider-agnostic router with structured outputs:** keeps every model
  call behind schemas and makes the provider replaceable.
- **ADR-0019, rule-first resolution:** a rule that can decide costs nothing and is
  deterministic; the LLM is asked only when no rule applies.

## Chapter: The ripple engine
<!-- \chapter{The Ripple Engine}\label{ch:engine} -->
### Write, wave, resolve
A change enters as a memory write: a new memory, a new version, or the expiry of a
temporary fact. The write's transaction opens the ChangeEvent, so even a change with no
dependents leaves history (I2). For an update, versioning copies every incoming
depends_on link of the old row to the new row (skipping dependents that are themselves
superseded history), copies every outgoing depends_on link re-pointed at each parent's
latest version, and leaves snapshot_of links on the old row (ADR-0014).

The engine (`ripple.core.engine.WaveEngine`) is a pure, synchronous iterator over a
snapshot of the dependency graph (docs/learning/ripple-engine.md). Wave one is every
depends_on dependent of the seed set, deduplicated and in first-seen order, never a seed.
After each wave the runner hands back outcomes; the engine keeps only changed ones
(update or retire), follows each update to its new version (whose links were copied),
and emits the unvisited dependents as the next wave. A visited set guarantees that a
memory reached through two changed parents is resolved once, with both in context, and
that cycles terminate. A depth limit is a safety net: a truncated ripple is reported and
shows up as stale kept in the benchmark. The graph is rebuilt from the store between
waves, because updates add links.

The runner (`ripple.core.ripple.RippleRunner`) gives each wave two commits
(docs/learning/ripple-runner-and-writes.md). The first marks the wave SUSPECT and records
the members as affected, so retrieval flags them at once. The resolver is then called
outside any transaction. The second commit applies the decisions: keep restores VALID,
retire retires, update writes a new version, and ask parks the memory in PENDING_USER and
marks its depends_on subtree SUSPECT, recording what it parked. Rows are re-read inside
the second commit, and a member that changed meanwhile is skipped and logged.

### Resolution
Resolution is rule-first (ADR-0019). A domain rule decides when it can; the jobs
eligibility rule, for example, compares the student's CGPA and batch with the opening's
cutoff and batch. A rule returns nothing when a parent is missing or in doubt, never a
guess. Only then is the LLM resolver called, with the trigger, the belief and its parents
as evidence in the user message, and its verdict is parsed into a schema whose
validators mirror the resolution (an update needs content, an ask needs a question), so
malformed verdicts are retried and never partly applied (I4).

### Asking the user, answers and expiry
An ask is a decision, not a failure. The asked memory waits in PENDING_USER, and the
memories below it are shown flagged. When the student answers, the parked memories are
restored first; "still holds" completes the event; "no longer holds" retires the memory
and ripples; a correction writes a new version and ripples. The nightly sweep retires
memories whose end date has passed and ripples each with trigger kind expiry, without an
LLM deciding that a date passed.

### Crashes, resumption and forget
Because each wave is two commits, a crash between them leaves an open ChangeEvent with
SUSPECT members. The nightly sweep finds open events older than a threshold and resumes
them: recorded decisions are replayed to rebuild the engine's visited set, and whatever
is still undecided is resolved. A per-event lease stops the sweep from resuming an event
a slow live ripple is still resolving (ADR-0099). Forget deletes a whole version chain
and its depends_on cascade, removes snapshot_of links, and writes one ForgetEvent, all in
one transaction (I7).

### Correctness argument
Correctness rests on three layers of tests. The engine's contract tests pin each rule
(direct dependents only, no seed in a wave, keep halts, the successor is followed after
an update, no revisits, cycles terminate, the depth limit truncates, determinism). The
invariant tests check I1 to I4 and I7 across trigger kinds. The hand-written scenario
suite (tests/scenarios) replays timelines covering a CGPA change, two consecutive
changes, a chain, temporary unavailability, an ask confirmed and an ask left unanswered,
a snapshot, a hidden link, forget, a moved deadline and a keep that halts a branch; the
bench smoke run passes {{num:smoke.ripple.scenarios_passed}} of
{{num:smoke.ripple.scenarios}} of these scenarios under the ripple strategy. The engine's
body was implemented by the collaborator at the author's request on 2026-10-31
(roadmap Phase 1, a task originally reserved for the author); TODO(author): review it
against the recipe in docs/learning/ripple-engine.md and defend its trade-offs.

## Chapter: Learning dependency links
<!-- \chapter{Learning Dependency Links}\label{ch:linker} -->
### The task and the baselines
A linker receives a new memory and a list of candidate memories and proposes typed links
in either direction; the write flow stamps each with its class from the domain's
registry and refuses unknown types (docs/learning/linking-and-intake.md). Three linkers
share the protocol:
- the **rule linker** proposes a link when one memory mentions a structured fact's
  attribute or value as a whole word, never between versions of the same fact; it is
  cheap and deterministic, with low recall on hidden links;
- the **LLM linker** sends candidates as JSON evidence and drops proposals naming
  unknown memories or types;
- the **trained linker** is the C1 model below.
Which one serves the write path is a configuration switch, with the LLM linker as the
default until H3 is judged (ADR-0128).

### Data
Labelled pairs (the C5 contract) are generated from the RippleBench jobs scenarios: every
(parent, dependent) pair in a scenario snapshot with its gold link type, plus pairs that
structure rules derive, each labelled with its provenance (ADR-0090). Negatives are
drawn at three per positive, and every reversed link is kept as a negative so the model
must learn direction (ADR-0091). Train and test are split by persona and template. Only
test pairs identical to a training pair are removed, so many test pairs still share one
memory text with training (counted in training/data/jobs_v0_pairs.manifest.json); this
is another reason to read the held_out=both cell. The jobs test split has
{{num:link.rule.jobs_v0.test_pairs}} pairs; {{num:link.rule.jobs_v0.test_pairs_both}} of
them are in the held_out=both cell, whose persona and template were both unseen in
training. Finance pairs come from the finance scenarios and are test only
({{num:link.rule.finance_v1.test_pairs}} pairs, ADR-0102). The labels are silver; a
stratified, blind hand check of link pairs is specified (ADR-0092) and is the author's
work, still to be done.

### Model and training
The model is ModernBERT-base, fine-tuned end to end on CPU with a linear head over the
jobs label space (the jobs link types plus "none"), class-weighted cross-entropy and
AdamW (ADR-0125, ADR-0126). Each memory is rendered as its kind, content and structured
triple, and a pair is a sentence pair (parent, dependent); serving scores both
orientations and proposes at most the more probable one. The epoch and decision
threshold are chosen on a validation persona. Three training seeds were run. The training
loop was a task reserved for the author (roadmap Phase 4) and was implemented by the
collaborator at the author's request on 2026-10-31.

### Results
Evaluation scores every pair independently, stratified by provenance and by held-out
cell (ADR-0093, ADR-0127). The cell to read is held_out=both: in the other cells the
template was seen in training and test pairs often share a memory text with training
pairs.

| linker | F1, held_out=both | precision | recall | typed F1 | F1, unseen persona only | F1, all test pairs |
|---|---|---|---|---|---|---|
| rule | {{num:link.rule.jobs_v0.f1_both}} | {{num:link.rule.jobs_v0.precision_both}} | {{num:link.rule.jobs_v0.recall_both}} | not typed | {{num:link.rule.jobs_v0.f1_persona}} | {{num:link.rule.jobs_v0.f1}} |
| trained, three-seed mean | {{num:link.trained.jobs_v0.f1_both}} | {{num:link.trained.jobs_v0.precision_both}} | {{num:link.trained.jobs_v0.recall_both}} | {{num:link.trained.jobs_v0.typed_f1_both}} | {{num:link.trained.jobs_v0.f1_persona}} | {{num:link.trained.jobs_v0.f1}} |
| LLM | {{num:link.llm.jobs_v0.f1_both}} | {{num:link.llm.jobs_v0.precision_both}} | {{num:link.llm.jobs_v0.recall_both}} | {{num:link.llm.jobs_v0.typed_f1_both}} | {{num:link.llm.jobs_v0.f1_persona}} | {{num:link.llm.jobs_v0.f1}} |

On held_out=both the trained linker is ahead of the rules by
{{num:link.jobs_v0.f1_both_trained_minus_rule_points}} points, which is less than the
spread between its own seeds (results/2026-10-31_linkpairs_summary_uncommitted); per
seed it is once below the rule linker, once level and once above. There is no evidence
of a difference. Where only the persona is new, the trained linker is far ahead, because
it has learned the templates' wording; that is memorisation of templates as much as
induction of dependencies. On pairs labelled by the scenario files (the links no
structure rule derives) the trained linker scores {{num:link.trained.jobs_v0.f1_scenario}}
against the rules' {{num:link.rule.jobs_v0.f1_scenario}}, which shows what the rules
cannot see. No seed proposed a reversed link, and all false positives were pairs from the
same scenario with no link (docs/results/link-finder.md).

**Transfer to finance (H4).** On finance the trained linker scores
{{num:link.trained.finance_v1.f1}} F1 against the rule linker's
{{num:link.rule.finance_v1.f1}}; the drop from the jobs held_out=both cell is
{{num:h4.transfer_difference_points}} points. Most finance link types are not in the jobs
label space, and the model made almost no positive predictions. H4 is not supported.

**Comparison with an LLM (H3) and cost.** The LLM row is pending: no valid provider key
was available, so H3 ({{num:h3.f1_difference_points}} points,
{{num:h3.cost_ratio}} of the cost) cannot be judged yet. Scoring a pair takes the
trained linker {{num:link.trained.jobs_v0.cpu_seconds_per_call}} CPU seconds on the
machine used, against {{num:link.rule.jobs_v0.cpu_seconds_per_call}} for the rules; the
provider-side cost of an LLM call is not comparable to CPU time and is reported, when it
exists, in dollars per thousand pairs. The hand-check agreement
({{num:handcheck.jobs_v0.agreement}}) is pending. Until it exists, the link-finder
numbers stay inside this draft.

## Chapter: Validity-aware retrieval
<!-- \chapter{Retrieval}\label{ch:retrieval} -->
### What retrieval must guarantee
The conversation and tailor agents answer from memory with citations (FR-10). For
Ripple's consistency work to be visible to the student, retrieval must never return a
retired belief and must mark every belief under review (I1). The one visibility rule
lives in core, and every retrieval path applies it last (docs/learning/retrieval.md).

### How it works
A search backend protocol offers lexical search, dense search and indexing. The
in-memory backend runs BM25 over each user's memories; the Postgres backend uses the
memories table itself as the index, with full-text ranking for the lexical path and a
pgvector column with an HNSW cosine index for the dense path. The dense embedding model
is not chosen yet (it needs its own ADR), so the dense path is pluggable and tested with a
deterministic fake embedder (ADR-0026). Lexical and dense candidates are fused by
reciprocal rank. The first hits that pass visibility become direct hits; the retriever
then expands one hop along the graph, to the live facts each hit depends on and its
snapshots, skipping history links whose parent has been superseded (ADR-0014), and gives
neighbours a reduced score. Visibility is applied to the whole result, and each item is
returned with its flag and evidence.

### What it is measured by
The stale retrieval rate (H2) is measured on this exact path: the benchmark's probe
queries the real hybrid retriever after every event (ADR-0120). The results chapter
reports it.

## Chapter: The job-hunt agent
<!-- \chapter{The Job-Hunt Agent}\label{ch:agent} -->
### The jobs domain adapter
An opening is an anchor memory plus one structured fact per field (cutoff, batch,
deadline, skills, location), each holding the span of the job description it came from
and linked to the anchor (ADR-0030). Profile facts are the student's CGPA and its scale,
batch and skills. Derived beliefs are eligibility (linked by eligibility_of), fit
(fit_of, with one reason line per required skill quoting the description), reminders
(reminder_for, forty-eight hours before a deadline) and the search criteria the Scout
filters with (criteria_from) (ADR-0031). The rules that compute them return nothing
rather than guess; a cutoff on a scale the rule cannot compare is left to the LLM or to
a question for the student (ADR-0034). Ranking orders openings by eligibility, then an
imminent deadline, then fit, then the earliest deadline, spreads companies within a tier,
never shows retired beliefs and flags suspect ones (ADR-0032). An invariant test checks
that every number and quoted phrase in a derived belief appears in its parents (I5).

### Intake
The job-description parser quotes the span for every field and drops any quote not found
in the text; regular expressions cross-check the cutoff and deadline, and a deadline
without a year is dropped rather than guessed (ADR-0035). Forwarded emails are stripped of
headers, quotes and signatures first. The resume parser extracts text with pypdf and
structures it with the LLM (ADR-0024). Parsed resume facts are stored as pending
candidates; no memory exists until the student confirms, and the confirmation runs the
ordinary intake (ADR-0043). Text that comes from a document is always treated as data,
inside fenced blocks in the user message, never as instructions.

### Agents
- The **conversation agent** (LangGraph, with a Postgres checkpointer, ADR-0023) handles
  four intents: telling it a fact (through intake), asking, planning, and answering a
  parked question. Answers keep only claims that cite memories retrieved in that turn,
  and flagged memories are marked unconfirmed (ADR-0045).
- The **tailor** is read-only and picks highlights for an opening from the student's own
  project and skill memories (ADR-0046).
- The **Scout** is a plain loop that runs nightly and when the criteria change
  (ADR-0072, ADR-0079). It fetches only through a sources package that enforces the
  allowed-sources registry: a terms note is required for each source, robots.txt is
  honoured and fails closed, requests are GET only and rate limited, and login pages are
  refused (ADR-0070, ADR-0008). As shipped, only forwarded emails are an active source;
  career pages stay disabled until a site agrees in writing. Deduplication uses the
  canonical URL, then a (company, title) fingerprint (ADR-0071).
- The **Curator** is the worker's nightly sweep: expiry, resumption of open ripples,
  and the weak-link re-check of FR-16.

### Delivery
- The **API** (FastAPI, ADR-0022) serves the memory inspector (list, detail with why it
  is held and its history, edit, forget), questions, resume and openings intake,
  recommendations, feedback, the graph for the map, and the account (Telegram link code,
  export, delete). Users are created by an administrator, and bearer tokens are stored
  only as hashes (ADR-0040). A test refuses any route that would apply for a job.
- The **worker** runs on arq and Redis (ADR-0017): the Scout, the sweep, the daily digest
  and hourly alerts, each per user under a lease, with a delivery log so a restart never
  resends (ADR-0055, ADR-0095).
- The **Telegram bot** accepts private chats, links an account with a one-use code, and
  offers questions, forget with a confirmation step, export and free-text conversation;
  production uses a webhook with a secret header (ADR-0025, ADR-0075 to ADR-0078).
- The **MCP server** exposes search, save, update, forget, explain, the open questions
  and answering them, over stdio for local clients and stateless streamable HTTP for the
  server, with one bearer token per connection (ADR-0006, ADR-0080 to ADR-0082). There is
  no apply tool.
- The **dashboard** is a Next.js static export with a client typed from the API's
  OpenAPI description (ADR-0085). Its pages cover today's recommendations, telling
  Ripple what changed, pasting an opening, reviewing a parsed resume, the memory
  inspector, open questions, and the account; the map draws openings, skills and
  applications as a React Flow graph from the inspector's links, with depends_on links
  solid and snapshot_of links dashed (ADR-0087, ADR-0088, ADR-0130, ADR-0131). A test
  keeps business logic off the client.
- **Running it:** one command starts an embedded Postgres with pgvector, applies the
  migrations, builds the dashboard and serves the API locally, with an optional demo seed
  (ADR-0132, ADR-0133); production is a Docker Compose stack on one server with TLS and a
  nightly database backup.
- **Hardening:** rate limits on writes, request ids, structured logs, security headers
  and size caps on requests and resume text (ADR-0098).

What is verified and what is not: these paths are covered by offline tests with fakes;
the Postgres, Redis, Telegram and container paths run only in CI or on a real server,
and no real message has been sent to a student yet (docs/05-roadmap.md).

### How the agent stays inside I5 and I6
I5 is enforced structurally: the resolver can only rewrite the content of an existing
belief, profile facts enter only through the intake of a student's own statement or a
confirmed parse, derived beliefs are computed from views over their parents, and an
invariant test checks their numbers and quotes against those parents. I6 is enforced at
every surface: the fetcher sends only GET requests to permitted sources, the API and MCP
tool lists have no apply action, the agents' capabilities are a closed set checked by a
test, and the bot may call only four Bot API methods.

## Chapter: RippleBench and methodology
<!-- \chapter{RippleBench}\label{ch:bench} -->
### Tracks
A RippleBench scenario declares memories, links, the resolutions an oracle would give,
and a timeline of events, each with the expected state of every labelled memory after it
(ADR-0061). The jobs track is generated from seeded personas and seven template families,
one per gold behaviour:

| family | jobs | news | finance |
|---|---|---|---|
| a changed fact | CGPA rises | a figure is revised | guidance is cut |
| an unrelated change | a deadline moves | another story develops | a peer's margin moves |
| a temporary fact | an exam block | a road closure | a trading halt |
| a dependency chain | an accepted offer | an attribution is retracted | a CEO departs |
| a belief the evidence cannot settle (ask) | an unknown cutoff | conflicting reports | a rate at an edge |
| a snapshot that must not move | a resume update | a shared note | a journal entry |
| a forget that must cascade | forget the CGPA | forget a story | forget a holding |

(Template names from docs/learning/bench-v1.md.) On the checked-in seed the jobs
track has {{num:oracle.v0.check_everything.scenarios}} scenarios with
{{num:oracle.v0.check_everything.checks}} gold checks. The news and finance tracks reuse
the same families in their own vocabularies (ADR-0100, ADR-0101); finance is test only,
the unseen domain for H4 (ADR-0102). All three are synthetic, with invented people,
companies and stories. Real news stories need the author's curation (ADR-0101). The
external STALE benchmark has a loader for a local copy, but whether its format maps onto
a memory API is open (ADR-0103).

### Splits, seeds and the replay harness
Train and test are split by persona and template, never by item; the test split is the
set of persona and template cells no link-finder training pair may come from. Each track
is generated with three generator seeds; the first reproduces the checked-in data, and
each seed redraws its own split (ADR-0121). The replay harness applies the events, hands
each open ChangeEvent to the strategy under test, and snapshots every memory after every
event, with the recommendations a placeholder ranking would show and the beliefs each was
based on (ADR-0062). A retrieval probe queries the real hybrid retriever after every
event (ADR-0120).

### Metrics
The metric definitions are fixed in ADR-0063 and implemented in ADR-0120, with two
wording amendments in ADR-0123:
- **update accuracy**, correct updates over should-change targets, and **dependent
  update accuracy**, the same without the memory the event itself wrote;
- **stale kept** and **wrongful changes** per scenario;
- **questions asked** per scenario;
- the **stale retrieval rate**, unflagged gold-stale probe results over all probe
  results;
- the **stale recommendation rate**, shown recommendations resting on a stale belief
  over shown recommendations (jobs only);
- **time to consistency**, and the share of should-change targets that never converged;
- **cost per ripple**, resolver calls per ChangeEvent, with tokens and dollars when an
  LLM is used.
Rates pool counts over scenarios before dividing.

### Baselines, fairness and protocol
All strategies share one store, one resolver, one clock and one counting wrapper around
the resolver, so their calls are comparable (ADR-0060). Check-everything re-resolves
every VALID memory after each write in one wave, applied parents first (ADR-0104).
Every run in this thesis uses the scripted oracle resolver and the scenario's own links,
which isolates the question of scope. The results/ folder of each run holds its
configuration, metrics, report and per-event snapshots, and the summary folder is
computed only from runs of the current code, refusing reruns that disagree (ADR-0120).
The numbers in this thesis are rendered from those folders by the macro pipeline and
checked by the I8 test (ADR-0110, ADR-0111). The metric bodies were a task reserved for
the author (roadmap Phase 3) and were implemented by the collaborator at the author's
request on 2026-10-31.

## Chapter: Results and discussion
<!-- \chapter{Results}\label{ch:results} -->
All values are seed means on the test split unless stated; the folders behind each are
listed in docs/paper/generated/draft/numbers.md, and
results/2026-10-31_benchsummary_uncommitted gives per-seed ranges. Every run used the
scripted oracle and gold links.

### Sanity replay
On the checked-in jobs data (every scenario, one seed), ripple passes
{{num:oracle.v0.ripple.pass_share}} of scenarios, check-everything
{{num:oracle.v0.check_everything.pass_share}}, newest-wins
{{num:oracle.v0.newest_wins.pass_share}} and append-only
{{num:oracle.v0.append_only.pass_share}}. Ripple fails
{{num:oracle.v0.ripple.checks_failed}} gold checks; check-everything fails
{{num:oracle.v0.check_everything.checks_failed}}. This is a correctness check of the
engine against its own specification: the gold and the oracle were written for
graph-scoped propagation.

### Q1 and H1: correctness and cost
| strategy | scenarios passed | update accuracy | dependent update accuracy | stale kept | cost per ripple |
|---|---|---|---|---|---|
| ripple | {{num:oracle_mem.v0.ripple.scenarios_passed}} of {{num:oracle_mem.v0.ripple.scenarios}} | {{num:oracle_mem.v0.ripple.update_accuracy}} | {{num:oracle_mem.v0.ripple.dependent_update_accuracy}} | {{num:oracle_mem.v0.ripple.stale_kept}} | {{num:oracle_mem.v0.ripple.cost_per_ripple}} |
| check-everything | {{num:oracle_mem.v0.check_everything.scenarios_passed}} of {{num:oracle_mem.v0.check_everything.scenarios}} | {{num:oracle_mem.v0.check_everything.update_accuracy}} | {{num:oracle_mem.v0.check_everything.dependent_update_accuracy}} | {{num:oracle_mem.v0.check_everything.stale_kept}} | {{num:oracle_mem.v0.check_everything.cost_per_ripple}} |
| newest-wins | {{num:oracle_mem.v0.newest_wins.scenarios_passed}} of {{num:oracle_mem.v0.newest_wins.scenarios}} | {{num:oracle_mem.v0.newest_wins.update_accuracy}} | {{num:oracle_mem.v0.newest_wins.dependent_update_accuracy}} | {{num:oracle_mem.v0.newest_wins.stale_kept}} | {{num:oracle_mem.v0.newest_wins.cost_per_ripple}} |
| append-only | {{num:oracle_mem.v0.append_only.scenarios_passed}} of {{num:oracle_mem.v0.append_only.scenarios}} | {{num:oracle_mem.v0.append_only.update_accuracy}} | {{num:oracle_mem.v0.append_only.dependent_update_accuracy}} | {{num:oracle_mem.v0.append_only.stale_kept}} | {{num:oracle_mem.v0.append_only.cost_per_ripple}} |

H1 compares ripple with check-everything:
| track | accuracy ratio | cost ratio |
|---|---|---|
| jobs | {{num:oracle_h1.v0.accuracy_ratio}} | {{num:oracle_h1.v0.cost_ratio}} |
| news | {{num:oracle_h1.news_v1.accuracy_ratio}} | {{num:oracle_h1.news_v1.cost_ratio}} |
| finance | {{num:oracle_h1.finance_v1.accuracy_ratio}} | {{num:oracle_h1.finance_v1.cost_ratio}} |

*Reading.* The accuracy half of H1 is met, but by construction: under the oracle ripple
meets gold, so the ratio cannot fall below one. Check-everything loses accuracy only in
the ask family, where its single wave re-decides the asked belief's dependent on its own
and leaves it VALID while gold wants it SUSPECT; that follows from the parents-first
order ADR-0104 chose, so the excess above one is a convention, not an advantage. The
cost half is not met: the target is under one fifth, and ripple uses
{{num:oracle_h1.v0.cost_ratio}} of check-everything's resolver calls on jobs. Both
strategies open the same ChangeEvents, so this is a like-for-like count. The scenario
stores are small, so re-checking everything is only a small multiple of the
graph-scoped cost; that the ratio would fall on larger stores is a prediction. The
measurement it needs, the same scenarios padded with unrelated memories at several
store sizes, is the first follow-up. The tracks mirror each other by family, so the news
and finance rows show the semantics carry across vocabularies; they are not independent
evidence.

The system-level H1, with the trained linker and an LLM resolver, is
{{num:h1.accuracy_ratio}} at {{num:h1.cost_ratio}}; the tokens and dollars per ripple
({{num:mem.ripple.tokens_per_ripple}}, {{num:mem.ripple.usd_per_ripple}}) wait for a
provider.

### H2: stale retrieval
| track | append-only | newest-wins | ripple | gap in points |
|---|---|---|---|---|
| jobs | {{num:oracle_mem.v0.append_only.stale_retrieval_rate}} | {{num:oracle_mem.v0.newest_wins.stale_retrieval_rate}} | {{num:oracle_mem.v0.ripple.stale_retrieval_rate}} | {{num:oracle_h2.v0.stale_retrieval_gap_points}} |
| news | {{num:oracle_mem.news_v1.append_only.stale_retrieval_rate}} | {{num:oracle_mem.news_v1.newest_wins.stale_retrieval_rate}} | {{num:oracle_mem.news_v1.ripple.stale_retrieval_rate}} | {{num:oracle_h2.news_v1.stale_retrieval_gap_points}} |
| finance | {{num:oracle_mem.finance_v1.append_only.stale_retrieval_rate}} | {{num:oracle_mem.finance_v1.newest_wins.stale_retrieval_rate}} | {{num:oracle_mem.finance_v1.ripple.stale_retrieval_rate}} | {{num:oracle_h2.finance_v1.stale_retrieval_gap_points}} |

*Reading.* H2 holds in direction. Superseded beliefs are retired and never retrieved
(I1), beliefs waiting for an answer are returned flagged, and flagged results are not
counted as stale. Newest-wins retires only the direct fact, so its stale dependents stay
visible, which is the dependent-belief problem in one number. The probe is close to the
worst case for strategies that keep old rows, since it queries each memory with its
first wording, and it counts every match rather than a top few. Ripple's zero depends on
gold links and on the oracle writing exactly the gold content. "Far below" has no
numeric target, and whether "standard memory retrieval" should be a Mem0-style system is
open. The system-level gap is {{num:h2.stale_retrieval_gap_points}} points.

### Q2 and C2: the action level
With the placeholder ranking on jobs, the share of shown recommendations resting on a
stale belief is {{num:oracle_mem.v0.ripple.stale_recommendation_rate}} for ripple,
{{num:oracle_mem.v0.check_everything.stale_recommendation_rate}} for check-everything,
{{num:oracle_mem.v0.newest_wins.stale_recommendation_rate}} for newest-wins and
{{num:oracle_mem.v0.append_only.stale_recommendation_rate}} for append-only. The share of
should-change targets that never reached gold is
{{num:oracle_mem.v0.ripple.ttc_share_never_converged}} for ripple,
{{num:oracle_mem.v0.check_everything.ttc_share_never_converged}} for check-everything,
{{num:oracle_mem.v0.newest_wins.ttc_share_never_converged}} for newest-wins and
{{num:oracle_mem.v0.append_only.ttc_share_never_converged}} for append-only. The
recommendation sample is small and the ranking a placeholder, so this shows the
measurement working rather than an effect at realistic scale; the pilot is where C2's
realistic form belongs.

### Ablations
| variant (jobs) | update accuracy | questions asked | cost per ripple |
|---|---|---|---|
| full ripple | {{num:oracle_mem.v0.ripple.update_accuracy}} | {{num:oracle_mem.v0.ripple.questions_asked}} | {{num:oracle_mem.v0.ripple.cost_per_ripple}} |
| without the graph | {{num:oracle_ablation.v0.no_graph.update_accuracy}} | {{num:oracle_ablation.v0.no_graph.questions_asked}} | {{num:oracle_ablation.v0.no_graph.cost_per_ripple}} |
| without asking the user | {{num:oracle_ablation.v0.no_ask_user.update_accuracy}} | {{num:oracle_ablation.v0.no_ask_user.questions_asked}} | {{num:oracle_ablation.v0.no_ask_user.cost_per_ripple}} |
| LLM linker instead of trained | {{num:ablation.llm_linker.update_accuracy}} | not measured | {{num:ablation.llm_linker.cost_per_ripple}} |
| without the Curator | {{num:ablation.no_curator.update_accuracy}} | not measured | {{num:ablation.no_curator.cost_per_ripple}} |
| without evidence retrieval | {{num:ablation.no_evidence.update_accuracy}} | not measured | {{num:ablation.no_evidence.cost_per_ripple}} |

*Reading.* Without the graph, ripple becomes check-everything in scope and cost, and
loses the ask family in the same way: the graph is what both saves calls and keeps the
subtree under an ask flagged. Without asking the user, update accuracy falls, because
the ask family's beliefs cannot be settled from the evidence. The model-backed ablations
need a provider key.

### Q4: the link finder
The link-finder chapter reports the results; in short, the trained linker is not
distinguishable from the rules on fully held-out jobs pairs
({{num:link.trained.jobs_v0.f1_both}} against {{num:link.rule.jobs_v0.f1_both}}), H4 is
not supported (a drop of {{num:h4.transfer_difference_points}} points to finance), and
H3 is pending.

### Discussion
The results answer the project's questions unevenly, and the thesis states them as they
are (docs/00-vision.md asks for answers whether the hypotheses hold or not):
- Q1: under the specified semantics, graph-scoped propagation keeps memory correct, and
  the baselines show how far simpler strategies fall from it. The evidence is
  semantic, not linguistic.
- Q2: stale beliefs are kept out of retrieval and out of the placeholder's
  recommendations; the realistic test is the pilot.
- Q3: graph scoping cuts the resolver calls to {{num:oracle_h1.v0.cost_ratio}} of
  check-everything's on these stores, short of H1's target; the scaling run decides
  whether the target is reachable at the store sizes a real student accumulates.
- Q4: a small model learns one domain's templates, not dependencies in general; the
  label space and data must span domains before transfer can be expected.
The largest risk for the full system is the link finder: every missing link is a belief
the ripple cannot reach, and every result above assumed gold links.

## Chapter: Pilot study (plan)
<!-- \chapter{Pilot Study}\label{ch:pilot} -->
The pilot (C3) has not run. This chapter records the plan as built so far, and the
metrics it will report.
- **Recruitment and consent.** A consent form and an onboarding script are drafts under
  docs/pilot, not to be used until the department and the guide approve them. Open
  review items include who may know who takes part, where the server runs, and the ethics
  contact. Participants get anonymous codes; the code-to-name list is kept on paper.
- **Operations.** The deployment readiness check, a restore drill and the consent
  approval come before the first student. Three incident severities and a daily
  monitoring check are defined for a one-operator pilot (ADR-0107).
- **Feedback.** Students mark recommendations saved, applied or dismissed and questions
  useful or not; one row per student, memory and kind, first statement wins (ADR-0105).
  "Applied" records the student's own statement; nothing is applied anywhere (I6).
- **Weekly report.** `python -m ripple.pilot.report` writes a weekly folder under
  results/pilot; weeks with too few active students are kept out of the shared report,
  and no user identifiers or notes are written (ADR-0106).
- **Metrics** (docs/pilot/metrics.md, a draft): {{num:pilot.students}} students;
  saved or applied share {{num:pilot.saved_or_applied_share}}; days earlier than
  self-discovery {{num:pilot.days_earlier_than_self_discovery}}; stale recommendation
  rate {{num:pilot.stale_recommendation_rate}}; question usefulness
  {{num:pilot.question_usefulness_share}}; self-reported trust {{num:pilot.trust_score}}.
  Two are computed by the weekly report today; the others wait for data and a survey
  ingestion step.
- **Qualitative findings** will be quoted only with consent.
The roadmap places a small pilot with classmates in Phase 3 and the main pilot in a
placement season (Phase 5); TODO(author): dates and department sign-off.

## Chapter: Ethics and privacy
<!-- \chapter{Ethics and Privacy}\label{ch:ethics} -->
- **The human applies.** The agent never submits an application or acts on an external
  site (I6, ADR-0008); the Scout reads only permitted sources and respects robots.txt,
  terms and rate limits. The enforcement points are listed in the product chapter.
- **No invented facts.** The agent never invents profile facts, experience or numbers
  (I5); every parsed field cites its span, and nothing enters memory without the
  student's confirmation.
- **Forget, export and delete.** Forget removes a whole version chain and everything
  that depends on it (I7). Export returns everything held about the student, including
  retired memories and events. Deleting the account forgets every memory and removes
  the candidates, uploads and the user (FR-15, ADR-0044). Known gap: ChangeEvents survive
  account deletion, so it is not yet a complete erasure; this is recorded as open in
  ADR-0044 and must be closed before the pilot.
- **DPDP alignment.** The design follows the principles of India's Digital Personal Data
  Protection Act, 2023 (NFR-3); whether it complies is for the reviewers to judge, and
  nothing here is legal advice.
- **Data minimisation.** The resume's text is stored, not the PDF; the dashboard has no
  analytics or third-party scripts; contacts, browsing data and location are not
  collected; traces carry no prompt or user content; conversation state keeps only the
  last few turns.
- **Third-party models.** A model call sends the relevant memory text to the provider;
  the consent form says so.
- **Untrusted text.** Retrieved and parsed text is evidence only, placed in user
  messages inside fenced blocks, never in system prompts.
- **Secrets** live only in the environment, never in the repository or images, and are
  never logged.
- **Finance** is an unseen-domain test; nothing gives financial advice (docs/00-vision.md).

## Chapter: Limitations
<!-- \chapter{Limitations}\label{ch:limits} -->
- **Synthetic, mirrored benchmarks.** All tracks are generated; they test consistency
  under labelled semantics, not language understanding, and v1 mirrors v0 by design.
- **Oracle resolver and gold links.** No result here includes a resolver's mistakes or a
  link finder's misses.
- **Unaudited gold and silver labels.** No sample of the gold states or the link labels
  has been hand-checked; all were written by one author.
- **Design seen against the benchmark.** Some decisions (the check-everything wave order,
  ADR-0104) were made with these tracks' outcomes in view.
- **H1 on small stores only.** The cost target is not met, and store size is not varied.
- **The link finder.** Indistinguishable from rules on fully held-out jobs pairs, and no
  transfer to finance; two of the three training runs did not record the base model's
  hub revision.
- **Pending evidence.** H3, tokens and dollars, the model-backed ablations, the hand
  check, the Mem0-style baseline, STALE and the pilot.
- **Single-machine, offline verification.** The Postgres, Redis, Telegram and container
  paths are verified only in CI or not yet; the evaluation ran on an uncommitted tree.

## Chapter: Conclusion and future work
<!-- \chapter{Conclusion}\label{ch:conclusion} -->
### Contributions revisited
- **C1, learned dependency induction:** a trained link finder exists, is served behind
  the Linker protocol and is evaluated with a held-out and a transfer protocol. On this
  evidence it does not yet beat rules on fully held-out pairs
  ({{num:link.jobs_v0.f1_both_trained_minus_rule_points}} points, within seed noise) and
  does not transfer ({{num:link.trained.finance_v1.f1}} on finance). The claim as stated
  is not supported yet; the comparison with an LLM linker is pending.
- **C2, action-level evaluation:** the benchmark measures recommendations and time to
  consistency beside memory states, and shows the action-level effect on the jobs track
  ({{num:oracle_mem.v0.append_only.stale_recommendation_rate}} of append-only's shown
  recommendations rest on a stale belief, {{num:oracle_mem.v0.ripple.stale_recommendation_rate}}
  of ripple's), at synthetic scale.
- **C3, the pilot:** the product, consent drafts, feedback capture and weekly reports
  are built; the pilot has not run.
- **C4, cost:** graph scoping uses {{num:oracle_h1.v0.cost_ratio}} of check-everything's
  resolver calls on jobs, short of H1's target on small stores; tokens and dollars are
  pending.

### Remaining work inside this project
These are planned steps, not future work: the store-size scaling run for H1; the LLM
linker comparison for H3 and LLM costs for C4; the hand check of link pairs; the
model-backed ablations; a Mem0-style baseline; the STALE mapping; real news stories;
closing the ChangeEvent erasure gap; the first commit and the citable re-run; and the
pilot.

### Future work beyond this project
- **Learned propagation strength.** The link schema carries a strength that nothing
  uses; damping a ripple by how much a dependent relies on its parent (docs/IDEAS.md) is
  a research question of its own.
- **Formal properties.** Relating the wave semantics to belief-revision postulates
  (minimal change, consistency) is a theory project this thesis does not attempt.
- **Shared and institutional memory.** Ripple's memories are per user; dependencies that
  cross users, such as a placement cell's cutoffs feeding many students' beliefs, raise
  questions of authority and privacy outside this scope.
- **Other domains.** The adapters show the core is domain-agnostic; a production agent in
  a second domain is a product of its own.

## Appendices
<!-- \appendix -->
- **ADR index.** docs/adr/README.md lists every decision with its status and the
  decisions it amends or supersedes.
- **Invariants and their tests.** tests/core/test_invariants.py, tests/llm and the
  module tests hold the named `test_invariant_I<n>_...` tests.
- **Reproducibility.** results/README.md describes the run folders. The benchmark grid is
  `uv run python -m bench.matrix` then `uv run python -m bench.summary`; the link finder
  is `training.train`, `training.evaluate` and `training.summarize`
  (docs/results/link-finder.md); the numbers are `uv run python -m paper.numbers`, with
  `--strict` as the camera-ready gate; the I8 check is `uv run python -m paper.i8`.
- **Consent form and onboarding** (docs/pilot), after the department's approval.
- **Glossary.** Memory, version, link, link class, ripple, wave, ChangeEvent, validity
  state, resolver, linker, oracle, gold.
