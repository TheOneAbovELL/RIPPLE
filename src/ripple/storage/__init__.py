"""SQL storage: SQLAlchemy tables, Alembic migrations, the Postgres Store (ADR-0016).

Imports ripple.core; nothing in core imports this package. Importing this package
registers every table on the shared metadata, so Alembic autogenerate and the
schema-drift test see the identity tables (migration 0003) and the retrieval columns
and indexes (migration 0004), the delivery log (0005), the resume uploads (0006) and the
pilot feedback (0009) as well as the core tables (0002).
"""

from ripple.storage import delivery_tables as _delivery_tables  # noqa: F401
from ripple.storage import feedback_tables as _feedback_tables  # noqa: F401
from ripple.storage import search_schema as _search_schema  # noqa: F401
from ripple.storage import tables as _tables  # noqa: F401
from ripple.storage import uploads_tables as _uploads_tables  # noqa: F401
from ripple.storage import users_tables as _users_tables  # noqa: F401
from ripple.storage.loop import use_selector_event_loop

# Every process that reaches Postgres imports this package first (tables register here),
# so the event-loop fix for psycopg on Windows lives here once rather than in each entry
# point (CLIs, workers, tests, the local run). A no-op off Windows (ADR-0115).
use_selector_event_loop()
