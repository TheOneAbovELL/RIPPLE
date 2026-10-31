---
paths:
  - "src/**/*.py"
  - "training/**/*.py"
  - "bench/**/*.py"
---
# Python rules
- Full type hints. pyright strict for src/ripple/core.
- Pydantic models for anything crossing a boundary (API, LLM, DB, MCP).
- core is pure: I/O only through injected interfaces (Store, LLMClient, Clock).
- Never call datetime.now() in core; inject a Clock so time logic is testable.
- Raise specific exceptions from ripple.core.errors. Never swallow exceptions.
- Structured logs with memory_id / trace_id. Never log secrets or full user messages at INFO.
- Async for I/O; no blocking calls inside async functions.
