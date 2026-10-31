"""Shared pytest configuration."""

from ripple.storage.loop import use_selector_event_loop

# psycopg's async mode cannot use Windows' default ProactorEventLoop; the slow suite runs
# against real Postgres, so every test loop is a selector loop (src/ripple/storage/loop.py).
use_selector_event_loop()
