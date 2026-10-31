# ADR-0008: The human applies; allowed sources only
Status: Accepted · Date: 2026-10-19

## Context
Auto-applying and scraping sites that forbid automation break terms of service and can
harm users.

## Decision
The agent never submits applications (I6). Scout uses only sources whose terms permit
automated access, plus content the user forwards. A registry records each source's terms
note; robots.txt and rate limits are respected.

## Alternatives considered
- Auto-apply — terms of service, quality and ethics problems.
- Scraping sites like LinkedIn — forbidden; account bans.

## Consequences
Smaller coverage, partly offset by forwarding.

## Revisit if
A source offers an official API that permits our use.
