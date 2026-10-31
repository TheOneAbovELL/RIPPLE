"""Event-loop compatibility for psycopg's async mode on Windows.

psycopg refuses asyncio's ProactorEventLoop, which is Windows' default; production runs
in Linux containers and never sees this, but a developer on Windows does (local tests,
migrations, the local run). Selector loops work everywhere, so entry points that drive
async Postgres call `use_selector_event_loop()` once before the first loop starts.
"""

import asyncio
import sys


def use_selector_event_loop() -> None:
    if sys.platform == "win32":
        # The policy class exists only on Windows; deprecated in 3.14, current for 3.12.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
