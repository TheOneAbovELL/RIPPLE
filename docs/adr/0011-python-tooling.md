# ADR-0011: Python tooling: uv, ruff, pyright, pytest
Status: Accepted · Date: 2026-10-19

## Context
We need fast, reproducible environments and strict checks from day one.

## Decision
Python 3.12+, uv for environments and locking, ruff for lint and format, pyright for types,
pytest for tests.

## Alternatives considered
- poetry / pip-tools — slower; more tools to maintain.
- black + flake8 + isort — three tools where ruff is one.
- mypy — fine, but pyright is faster with better editor integration.

## Consequences
The team (the author) learns uv.

## Revisit if
A required library does not support Python 3.12+.
