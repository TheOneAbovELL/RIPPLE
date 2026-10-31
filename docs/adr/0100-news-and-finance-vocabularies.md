# ADR-0100: Minimal news and finance adapters are vocabularies mapped onto the core link classes
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-15, wave B)

## Context
docs/00 scopes news as "benchmark only" and finance as "unseen-domain test + small
demo"; docs/04 adds a news track and a test-only finance track to RippleBench. The
scenario runner must write memories and links in those domains, and the link finder's
transfer test (H4) needs finance link types with a class each. ADR-0013 fixes how a
domain plugs in: it declares link types and maps each to depends_on or snapshot_of;
core stays untouched. The jobs adapter's `vocabulary.py` is the model.

## Decision
1. `src/ripple/domains/news/vocabulary.py` and `src/ripple/domains/finance/vocabulary.py`
   hold only vocabulary: DOMAIN, `Kind`, attribute enums, a subject helper and a link
   type -> class mapping wrapped by `news_registry()` / `finance_registry()` on
   `ripple.core.links.LinkTypeRegistry`. No sources, parsers, rules or ranking.
2. News: kinds fact, derived, claim, summary, briefing, shared; link types
   summarises, inferred_from, briefing_from (depends_on) and shared_from (snapshot_of:
   what the reader already passed on is a record and a correction never rewrites it).
3. Finance: kinds fact, derived, assumption, thesis, alert, journal; link types
   premise_of, estimate_from, alert_for (depends_on) and journaled_with (snapshot_of:
   a journal entry records a past decision as it was made).
4. Each domain has exactly one snapshot_of type so every track has a "correct
   non-update" family, as sent_with_resume gives jobs.
5. Names do not collide with jobs or with each other, so one registry can hold all
   three (tested).

## Alternatives considered
- Generic types only (depends_on_fact) for news and finance — no adapter code at all,
  but H4 then measures nothing about typed links, and the snapshot case cannot be
  expressed without a typed snapshot_of link. Lost.
- Full adapters with rules and ranking like jobs — out of scope for benchmark-only
  domains and would invite finance "recommendations" (docs/00 rules out advice). Lost.
- Reusing jobs names where the meaning is close (reminder_for for alerts) — one name
  with two meanings across domains confuses the link finder's labels. Lost.

## Consequences
- Adding a type is one line; the bench's `validate_scenario` refuses a type the
  scenario's domain does not know (bench/domains.py).
- Kinds and attributes are a proposal for the author: curated real stories or a finance
  demo may need more, added the same way.
- The adapters import core only (tested); nothing outside the bench uses them yet.

## Revisit if
Curated news stories need a behaviour neither class expresses, or a finance demo
(roadmap Phase 5) needs rules of its own.
