"""Domain-agnostic core. Today: clock, ids, errors. Phase 1 adds models, the Store
protocol, the ripple engine and the Linker and Resolver protocols.

Must not import ripple.llm, ripple.linking, ripple.agents, ripple.api, ripple.domains or any
framework (see tests/core/test_boundaries.py).
"""
