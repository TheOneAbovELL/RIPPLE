# ripple.agents.scout and ripple.domains.jobs.sources: the Scout
Written 2026-10-24 (WS-9) for src/ripple/agents/scout.py,
src/ripple/domains/jobs/sources/{registry, canonical, ratelimit, cache, robots, fetcher,
extract, dedupe, report, wiring}.py, the `scout_run` body in src/ripple/worker/jobs.py
and config/sources.yaml. ADRs 0070 (registry), 0071 (dedupe), 0072 (agent shape).

## 1. What it does
Every night, and whenever a student's search criteria change, the Scout fetches the
sources the author has permission for, turns each listing into candidate job
descriptions, drops what the student already holds or has already been judged, parses
the rest with the JD parser, skips what the student cannot apply to, and records the
remainder as openings with their derived beliefs, so the digest can rank them. It never
submits anything, never logs in, never leaves the registered hosts.

## 2. Why it exists
FR-8 (daily schedule and on criteria change; allowed sources only; dedupe), FR-2
(openings with source spans), ADR-0008 (the human applies; allowed sources only),
I5 (no invented facts), I6 (no action on external sites). It is the piece that makes
the digest non-empty without the student pasting every JD by hand.

## 3. How it works
- `sources.registry.load_registry(path)` reads config/sources.yaml into
  `SourceRegistry`: `user_agent` plus `SourceSpec`s (id, kind, url, terms_note,
  robots_respected, rate_limit_per_minute, parser hint, enabled). A blank terms note,
  `robots_respected: false`, a URL with credentials, an unknown field or a career page
  without a hint all raise `SourceRegistryError`. `registry.fetchable()` is the enabled
  career pages and public APIs; forwarded email is listed but never fetched.
- `sources.fetcher.SourceFetcher.fetch(source, url=None)` is the only code that sends
  a request. Order per fetch: host must equal the source's host; `canonical_url`;
  `RobotsPolicy.allows` (robots.txt fetched once per host per run through the same
  rate-limited GET; 4xx = allow all, 5xx or timeout = host closed for the run); the
  source's `TokenBucket` (one token, refilled at the registry rate or robots'
  Crawl-delay, whichever is slower); cookies cleared; GET with our User-Agent and the
  cache's If-None-Match / If-Modified-Since. Then: 304 → cached body; 401/403/407 or
  WWW-Authenticate → `FetchRefusedError`; 3xx → same-host only, at most three; 429/5xx
  and transport errors → exponential backoff (Retry-After honoured up to 60 s), then
  `FetchFailedError`; other 4xx → `FetchFailedError` at once; 200 → cached when it has
  validators, body capped at 2 MB.
- `sources.extract.extract_candidates(body, content_type, page_url, hint)`: HTML
  through the stdlib parser into a small tree and a CSS selector subset (`li.job`,
  `#openings > li`, `a[href]`, comma alternatives); each match becomes a `Candidate`
  (text, first link resolved against the page, heading or first line as title). JSON
  through dotted paths (`data.jobs`, `description`, `url`, `title`); an HTML
  description is flattened to text. `page_text(html, selector)` gives a detail page's
  JD body.
- `sources.dedupe.OpeningDeduplicator`: `known_url` checks the ledger, then the
  user's opening anchors (`scout:<id>:<canonical>` refs, any status) and any
  `source_url` field; `known_fingerprint` checks the ledger, then every held
  (company, title) pair; `remember` marks `url:` and `fp:` keys. `ScoutLedger` is the
  seen set (in memory now; Postgres table with migration 0007 is the follow-up).
- `agents.scout.ScoutAgent.run_for_user(user_id)`: reads the VALID criteria memory
  into `ScoutCriteria` (cgpa, batch, skills; no criteria = no filter); for each
  fetchable source: fetch the listing, extract, cap at 25 candidates; per candidate:
  canonical URL → `known_url` (no model call for a known URL) → skip if the
  `filtered:<criteria digest>:<url>` key is set → fetch the detail page when the hint
  says `follow_links` and take `detail_selector` text → `parse_jd` with source_ref
  `scout:<id>:<url>` → no title: mark `url:` and skip → `known_fingerprint` → criteria
  filter (mark the filtered key) → `record_opening` → `derive_for_opening` →
  `remember`. Returns a `ScoutReport` with per-source counts (candidates, new, duplicates,
  filtered, refused, errors), the error list with URLs (refusals are policy, counted
  but not listed as errors), and the recorded anchor ids. Nothing a
  source or candidate does can raise out of the run.
- `worker.jobs.scout_run(context, scout=None)`: builds the agent for the run
  (`open_scout` over `open_fetcher`, registry from `RIPPLE_SOURCES_CONFIG`, Router from
  `RIPPLE_LLM_CONFIG`) unless one is injected, then per active user: lease
  `scout:<user>` for 45 minutes, run, log; failures isolated and raised at the end as
  `JobFailedForUsersError`. Returns `ScoutRunReport`.
- Criteria change: `event_changed_criteria(store, event)` says whether a completed
  ChangeEvent created or updated a criteria memory; the caller then invokes
  `ScoutTrigger.on_criteria_changed(user_id)` (`ImmediateScoutTrigger` in process,
  `EnqueueingScoutTrigger` to the worker queue). The hook itself sits in the
  coordinator's write flow (see the WS-9 handover).

## 4. Trade-offs
- A plain loop instead of a LangGraph graph: nothing in the loop branches on model
  output, so a graph would add a checkpointer for no resume benefit. Wrong when: a
  source needs multi-step navigation decided by a model; that would be a different
  agent anyway (and probably a terms-of-service problem).
- Fail closed on robots.txt and on a bad registry: a host whose robots.txt errors is
  skipped for the run; a malformed registry stops every user's run. Chosen because
  the cost of a missed night is one digest, the cost of an unpermitted fetch is trust.
- URL dedupe before the model, fingerprint after: saves most model calls on a nightly
  listing; a same-role repost under a new URL still costs one parse before it is
  recognised.
- The filtered mark is keyed by the criteria digest: a CGPA rise re-judges every
  excluded JD once (one parse each), instead of every night or never.
- Only cutoff and batch filter; skills do not: a graded fit (ADR-0031) is more useful
  than a hard skill filter that hides a reachable opening.
- The ledger is per process: restarts lose the filtered and not-a-JD marks (one
  re-parse each), never the recorded ones, which the store answers.
- Hand-written selector subset: no dependency; wrong when a permitted site needs
  sibling or pseudo selectors, at which point ADR-0070 says to revisit.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| A source without a terms note is fetched | test_parse_registry_refuses_a_source_without_a_terms_note, ..._a_blank_terms_note |
| `robots_respected: false` accepted | test_parse_registry_refuses_robots_respected_false |
| Default file fetches something before the author enables it | test_default_sources_file_lists_only_forwarded_email_and_a_disabled_example |
| A POST, a login, an off-host fetch, a cookie session | test_invariant_I6_scout_only_gets_allowed_sources, test_fetcher_refuses_a_login_response_..., test_fetcher_refuses_a_redirect_to_another_host, test_fetcher_never_keeps_a_cookie_between_requests, test_fetcher_refuses_a_url_on_another_host_without_sending_anything |
| robots.txt ignored or fetched per URL | test_fetcher_refuses_a_path_robots_txt_disallows_..., test_robots_policy_fetches_robots_txt_once_per_host_per_run, test_robots_policy_closes_the_host_when_robots_txt_cannot_be_read |
| Requests faster than the site allows | test_fetcher_spaces_requests_to_one_source_by_its_rate_limit, test_fetcher_slows_down_to_the_crawl_delay_..., test_token_bucket_* |
| Retry storm on a 4xx; no retry on a 5xx | test_fetcher_does_not_retry_a_404, test_fetcher_retries_a_5xx_with_exponential_backoff_then_succeeds, test_fetcher_raises_after_retries_are_exhausted |
| Re-downloading an unchanged page | test_fetcher_revalidates_with_if_none_match_and_serves_the_cached_body_on_304 |
| Script text or nav chrome reaches the parser | test_html_candidates_skip_script_and_style_text, test_scout_uses_only_the_jd_text_from_the_detail_selector_in_the_parser_call |
| Tracking parameters make one URL two | test_canonical_url_normalises_..., test_canonical_url_is_idempotent |
| Same role, two URLs | test_scout_treats_a_same_role_from_another_url_as_a_duplicate_by_fingerprint, test_fingerprint_* |
| A known JD costs a model call every night | test_scout_second_run_counts_duplicates_and_filtered_without_a_model_call |
| A CGPA rise never lets a filtered opening back in | test_scout_reparses_a_filtered_opening_once_the_criteria_change |
| A recorded field is not the page's words | test_invariant_I5_scout_records_only_parsed_fields_with_spans_into_the_page_text |
| One failing source stops the run | test_scout_counts_a_failing_source_and_continues_with_the_next |
| Unbounded model calls per source | test_scout_caps_the_candidates_parsed_per_source |
| Two workers scout one user at once | test_scout_run_skips_a_user_whose_lease_is_held |
| One user's failure hides the others | test_scout_run_isolates_a_failing_user_and_raises_at_the_end |
| Openings never reach the digest | test_scout_openings_reach_the_daily_digest |

## 6. Interview questions
1. *Where is I6 enforced, and why is it not in the agent?* In `SourceFetcher`, the only
   code that sends requests: host check, robots, GET only, same-host redirects, no
   cookies, login responses refused. The agent only receives a fetcher, which is also
   why the agents import scan (no `httpx` in `ripple.agents`) keeps passing.
2. *How does the Scout avoid paying a model call for the same JD every night?* The
   canonical URL is checked against the ledger and the store before the parse; the
   fingerprint after. The store check uses the `scout:<id>:<canonical>` source_ref, so
   it survives a restart.
3. *What happens when the student's CGPA rises?* The ripple writes a new criteria
   memory; its content digest changes, so the `filtered:<digest>:<url>` marks of the old
   criteria no longer match and every excluded JD is parsed and judged once more.
4. *Why does a 5xx on robots.txt close the host but a 404 open it?* The protocol says
   no robots.txt means no restrictions; an unreadable one means we do not know the
   restrictions, and ADR-0008 says unknown is closed.
5. *Why do fields recorded by the Scout cite the detail page text and not the listing
   card?* The parser is given the `detail_selector` text, and `record_opening` checks
   every span against the text it was given (`raw_text[start:end] == span.text`), so
   the card's summary can never become a fact with a span into the wrong document.
6. *Bonus: why is `forwarded_email` in a registry of things to fetch?* So the registry
   is the complete answer to "where do openings come from", including the channel that
   needs no fetch; the loader enforces that it has no URL.

## 7. Exercise
Add pagination to a career page: a `next_selector` hint whose link, when present and on
the same host, is fetched after the listing until it is absent or a page cap is hit.
Decide before coding how the cap interacts with `max_candidates_per_source`, what
happens when page 2 is robots-disallowed, and which I6 test must be extended.
