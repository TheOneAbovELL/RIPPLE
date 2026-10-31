# Ideas backlog
One line per idea. Status: idea | proposed | approved | implemented | rejected.
Tier A ideas are implemented directly and recorded in DEVLOG; Tier B ideas get a
proposal in docs/proposals/ and wait for the author.

| # | Idea | Tier | Status | Link |
|---|---|---|---|---|
| 1 | Wave-by-wave ripple with early stopping | B | approved, ADR accepted 2026-10-19 | docs/adr/0013-wave-by-wave-ripple-link-classes.md |
| 2 | Rule-first resolution: domain rules resolve computable beliefs before the LLM | B | approved, ADR-0019; chain built, jobs rules in Phase 2 | docs/proposals/0001-rule-first-resolution.md |
| 3 | Self-expiring memories via valid_to, ripple on expiry | B | approved, ADR accepted 2026-10-19 | docs/adr/0015-change-is-memory-write-self-expiry.md |
| 4 | Structure-derived silver labels + candidate pre-filter for the link finder | B | proposed | docs/proposals/0002-silver-labels-and-candidate-prefilter.md |
| 5 | Time-to-consistency as an action-level metric with a replay harness | B | proposed | docs/proposals/0003-time-to-consistency.md |
| 6 | Link strength as propagation damping (strong link → SUSPECT, weak link → ask) | B | idea | section 15 of the original project proposal |
| 7 | RippleBench v1 generator: missing-link scenarios (Linker in the loop), multi-parent same-wave cases, prose fields for the change detector | B | idea | WS-7 handover |
| 8 | Postgres DeliveryLog and a per-ChangeEvent lease so a worker restart cannot resend a digest or double-resolve a ripple | A | done 2026-10-26 (ADR-0095, ADR-0099; Postgres paths unverified locally) | WS-6 handover |
| 9 | Eligibility rule honours ProfileAttribute.CGPA_SCALE (10 vs 4 point) instead of comparing raw numbers | B | done 2026-10-26 (ADR-0034: derivation and rule defer off the cutoff scale; criteria drop the CGPA gate) | WS-2 handover |
| 10 | JD parser recognises a cutoff written on another scale ("3.0/4") and drops or flags it instead of reading it as ten-point | A | idea | ADR-0034 consequences |
| 11 | Postgres ledgers for the Scout (migration 0007) and Telegram updates (migration 0008) so restarts forget nothing | A | idea | ws-9.md, ws-10.md |
| 12 | Per-item digest snapshot so the pilot report can compute the stale-recommendation rate and the saved/applied share's denominator | B | idea | ws-16.md, ADR-0106 |
| 13 | Survey ingestion command for the pilot's self-reported trust and usefulness questions | A | idea | ws-16.md |
| 14 | Ranking track over candidate sets, so the LLM linker's write-time cost is measured as deployed rather than per single pair | B | idea | ADR-0093 |
| 15 | LLMLinker exposes per-call usage (model served, tokens, cost) so the link-pair harness can report H3 cost and refuse fallback runs | A | idea | ws-14.md |
| 16 | Feedback buttons on digest and alert items: needs the outbound Transport to carry an inline keyboard | A | idea | ws-16.md |
| 17 | Producers write what paper/registry.py reads: bench.run memory_metrics object, real llm_calls and served model ids, ablation and linker keys; training.evaluate usd_per_1k_pairs and a strict_test split; a pilot season summary folder | A | idea | ws-17.md requests 1-3 |
| 18 | I8 detector sees bare integers in tables and numbers written in words (today it does not) | A | idea | ADR-0111 |
