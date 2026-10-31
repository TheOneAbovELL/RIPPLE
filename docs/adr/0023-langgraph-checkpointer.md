# ADR-0023: LangGraph dependency and Postgres checkpointer
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
ADR-0005 chose LangGraph for agents without pinning the package or deciding where
checkpoints live. Durable checkpoints and human-in-the-loop pauses were the reason for
choosing it; they need a persistent saver.

## Decision
`langgraph` and `langgraph-checkpoint-postgres` with exact pins. Production agents
checkpoint into the same PostgreSQL database (ADR-0004), in LangGraph's own tables,
set up by its `setup()` at service start, outside Alembic. Tests use LangGraph's
in-memory saver so they stay offline (NFR-1). `ripple.core` never imports LangGraph
(boundary test).

## Alternatives considered
- SQLite checkpointer — a second database for one concern. Lost.
- No checkpointer — loses the interrupt/resume that justified LangGraph. Lost.
- Managing LangGraph's tables through Alembic — couples our migrations to a
  third party's schema. Lost; the tables are theirs.

## Consequences
- Agent state and memory state live in one database but are not transactionally
  linked; a memory write is final when its ChangeEvent commits, whatever the agent
  checkpoint says.
- Pulls in langchain-core transitively; contained to ripple.agents.

## Revisit if
LangGraph's checkpoint API changes incompatibly, or the pilot shows checkpoint growth
that needs a retention policy.
