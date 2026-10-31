# ADR-0071: Scout dedupe by canonical URL, then (company, title) fingerprint, with a seen ledger
Status: Accepted under the autonomous mandate · Date: 2026-10-24 (WS-9)

## Context
FR-8 asks for dedupe. The same opening reaches the Scout as `/jobs/42`,
`/jobs/42/?utm_source=mail` and `/jobs/42#apply`; the same role reaches it from two
sources with no URL in common; and a JD the Scout already judged (recorded, filtered
out, or not a JD at all) is on the same listing page every night. Each model call costs
money and each duplicate memory is noise in the ripple graph. `record_opening`
(ADR-0030) already refuses a second live opening with the same `source_ref`, but only
after the parse and only for the exact string.

## Decision
1. **Canonical URL** (`sources.canonical.canonical_url`): lower-case scheme and host,
   credentials dropped, default port dropped, fragment dropped, `utm_*` and the usual
   click identifiers dropped, remaining query sorted, repeated and trailing slashes
   removed. It is idempotent and a pure function.
2. **The anchor's `source_ref` is `scout:<source id>:<canonical url>`**, so the store
   itself answers "have I recorded this URL" across restarts: `OpeningDeduplicator`
   reads the user's opening anchors (any status: a closed opening re-found is still the
   same opening) and the `source_url` fields of openings the user pasted, and compares
   canonical forms. An API item with no URL gets `<listing url>#item-<12 hex of its
   text>` so two items never share a ref.
3. **Fingerprint** `(company, title)`: case-folded, punctuation and spacing removed,
   `&` read as `and`, legal suffixes (pvt, ltd, inc, llc, …) dropped from the company.
   Checked after the parse, against the title and company fields of every opening the
   user holds; a match counts as a duplicate and the URL is remembered.
4. **Order of checks**: URL before the model call (cheap, saves the parse), fingerprint
   after it (needs the parsed company and title). An `OpeningAlreadyRecordedError`
   from the adapter is a third, last line and is counted as a duplicate.
5. **`ScoutLedger`**: a `(user_id, key)` set with `seen` / `mark`. Keys:
   `url:<canonical>` for anything recorded, duplicate or not a JD; `fp:<fingerprint>`
   for recorded roles; `filtered:<criteria digest>:<canonical>` for a JD the criteria
   excluded. The criteria digest in the key is what lets a CGPA rise bring an opening
   back: a new criteria memory has a new digest, so the JD is parsed and judged again.
   The in-memory ledger lives for the worker process; the Postgres table is a
   follow-up with migration id 0007 reserved (handover). The store check in point 2
   covers restarts for everything recorded, so only filtered and not-a-JD marks are
   lost with the process.

## Alternatives considered
- Dedupe by exact URL only: misses tracking parameters and trailing slashes on the
  first real site; too weak.
- Fingerprint on title only: two companies hiring "Software Engineer Intern" are two
  openings; too strong.
- Fuzzy title matching (edit distance, embeddings): a probabilistic duplicate decision
  the student cannot audit; the exact normalised key is explainable and, when it
  misses, the cost is one extra opening, not a lost one.
- Let `record_opening` be the only dedupe: it runs after the model call, so every
  nightly listing would re-parse every JD.
- Forget the filtered mark on every run: simple, but re-parses every excluded JD every
  night for every user; the digest-keyed mark keeps the re-judgement to criteria changes.

## Consequences
- The Scout's model calls per night approach the number of genuinely new JDs.
- A forgotten opening (I7) stays forgotten: its URL key remains in the ledger, so the
  Scout does not re-add what the user erased, for the life of the process (and of the
  table once it exists).
- Openings the user pasted and the Scout then finds are recognised through the
  `source_url` field only when the JD text contained its URL; otherwise the fingerprint
  catches them after one parse.

## Revisit if
Pilot sources repost the same role under new URLs and new titles ("SDE Intern" vs
"Software Engineer Intern"); then a normalised-title synonym table belongs in the
jobs adapter, still deterministic.
