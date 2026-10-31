"""What an agent graph is allowed to do (I6).

Each agent declares the capabilities its nodes use. The set is closed: everything an
agent can reach is memory, the Router, the answers API or, for the Scout only, a GET
through the allowed-sources fetcher (ADR-0070). Nothing here fills a form or submits
anything; tests/agents/test_invariants_agents.py checks each
agent's declaration against this enum and scans the package's imports.
"""

from enum import StrEnum


class Capability(StrEnum):
    LLM_COMPLETE = "llm.complete"  # ripple.llm.Router, schema-validated (I4)
    MEMORY_READ = "memory.read"  # Store reads
    MEMORY_RETRIEVE = "memory.retrieve"  # Retriever.search (C2)
    MEMORY_WRITE_VIA_INTAKE = "memory.write_via_intake"  # ripple.core.intake.Intake.ingest
    MEMORY_ANSWER_QUESTION = "memory.answer_question"  # ripple.core.answers
    # Scout only (ADR-0072): GET requests to registered hosts through
    # ripple.domains.jobs.sources, robots and terms enforced there (ADR-0008).
    SOURCES_READ = "sources.read"
    MEMORY_WRITE_OPENING = "memory.write_opening"  # ripple.domains.jobs.openings.record_opening
    MEMORY_WRITE_DERIVED = "memory.write_derived"  # ripple.domains.jobs.derive.derive_for_opening
