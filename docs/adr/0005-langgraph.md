# ADR-0005: LangGraph for agents; core stays framework-free
Status: Accepted · Date: 2026-10-19

## Context
Agents need durable state, retries, human-in-the-loop pauses and background runs.

## Decision
Agent graphs use LangGraph. src/ripple/core never imports it.

## Alternatives considered
- Hand-rolled loops — would reinvent checkpointing and interrupts.
- Other agent frameworks — no clear advantage; the author already knows LangGraph.

## Consequences
Exposure to framework churn, contained to src/ripple/agents.

## Revisit if
A LangGraph limitation blocks a requirement.
