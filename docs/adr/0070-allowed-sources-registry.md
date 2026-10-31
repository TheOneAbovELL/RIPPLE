# ADR-0070: Allowed-sources registry: a YAML file validated into Pydantic, terms note required
Status: Accepted under the autonomous mandate · Date: 2026-10-24 (WS-9)

## Context
ADR-0008 says the Scout uses only sources whose terms permit automated access, plus
what the user forwards, and that a registry records each source's terms note while
robots.txt and rate limits are respected. FR-8 needs the Scout to run daily and on a
criteria change. Nothing in the code so far could name a source; the question is what
the registry is, who may add to it, and what the Scout may do with an entry.

## Decision
1. **One file, `config/sources.yaml`**, read through `RIPPLE_SOURCES_CONFIG` (default
   `config/sources.yaml`), validated into `SourceRegistry` /
   `SourceSpec` (`ripple.domains.jobs.sources.registry`). Fields per source: `id`,
   `kind` (`public_api` | `career_page` | `forwarded_email`), `url`, `terms_note`,
   `robots_respected`, `rate_limit_per_minute`, `parser` (an `ExtractionHint`),
   `enabled`. The file also carries the `user_agent` the Scout identifies itself with.
2. **A source without a terms note does not load.** `terms_note` must be non-blank;
   `robots_respected` is typed `Literal[True]`, so `false` is a validation error, not a
   setting; `rate_limit_per_minute` is bounded to 1..600; unknown fields are refused;
   a `url` with credentials or a non-http(s) scheme is refused. A validation failure
   raises `SourceRegistryError` (a `ConfigurationError`) with every problem listed, so
   the worker refuses to start its scout run on a bad file rather than skipping entries.
3. **Kinds decide what is fetched.** `forwarded_email` has no URL and is never fetched:
   it exists so the registry is the complete list of where openings come from. A
   `career_page` needs a CSS selector or a JSON items path; a `public_api` needs JSON
   items and text paths. Only `enabled` sources of the other two kinds are fetchable.
4. **The default file lists the forwarded-email source and one example career page
   marked `enabled: false`** with a PLACEHOLDER terms note. The author enables a career
   page only after the site has confirmed permission in writing, and replaces the note
   with the date and the source of that permission.
5. **Extraction hints, not scrapers.** A hint is a CSS selector subset (tag, class,
   id, attribute, descendant, child, comma) over the standard library's HTML parser, or
   dotted JSON paths. No HTML library is added: the pilot's sources are a handful of
   pages whose hints the author writes by hand after reading the page, not the open web.

## Alternatives considered
- Sources in the database with an admin endpoint: lets a user add a site, which is
  exactly what ADR-0008 forbids; the permission is a human decision recorded in a
  reviewed file. Revisit for a multi-tenant deployment.
- Sources hard-coded in Python: no validation story, and a URL change is a code change.
- BeautifulSoup / lxml for extraction: a new dependency for a selector subset the
  pilot does not need; the hand-written subset is tested and sufficient for cards and
  article bodies. Revisit if a permitted site needs sibling or pseudo selectors.
- Treating a missing terms note as a warning: a warning is ignored; a refusal is read.

## Consequences
- Coverage in the pilot is only what the author has permission for; forwarding stays
  the main intake, as ADR-0008 anticipated.
- The registry is the single place a reviewer checks to answer "what does the Scout
  fetch and on what authority"; the fetcher refuses any host not in it (ADR-0072, I6).
- A broken registry stops every user's scout run, by design (fail closed).

## Revisit if
A source offers an official API with per-user terms (then the terms note may need a
per-user acceptance record), or the pilot needs more than a handful of sources.
