"""Background jobs (ADR-0017): nightly sweep, daily digest, hourly alerts; Scout in Phase 3.

Import `ripple.worker.jobs` for the testable job functions and
`ripple.worker.settings` only in the arq process (it reads REDIS_URL at import).
"""
