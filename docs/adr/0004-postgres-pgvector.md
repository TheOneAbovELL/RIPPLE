# ADR-0004: PostgreSQL + pgvector with in-process traversal
Status: Accepted · Date: 2026-10-19

## Context
We need relational data (memories, links, history), vectors, and transactional commits.

## Decision
One PostgreSQL database with pgvector. Per-user graphs are loaded and traversed in Python;
recursive SQL if needed later.

## Alternatives considered
- Neo4j — an extra service; per-user graphs are small.
- Qdrant + Postgres — two stores to keep consistent.
- SQLite — weaker concurrency and vector support for a multi-user pilot.

## Consequences
One backup and migration story; ripple commits are atomic.

## Revisit if
A user graph exceeds ~100k memories or traversal p95 exceeds its NFR target.
