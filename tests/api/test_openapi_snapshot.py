"""The dashboard's committed OpenAPI snapshot matches the live API (WS-12 handover)."""

import json
from pathlib import Path

from tests.api.harness import Harness

SNAPSHOT = Path(__file__).resolve().parents[2] / "apps" / "web" / "openapi.json"


def test_dashboard_openapi_snapshot_matches_the_api() -> None:
    live = Harness.build().app.openapi()
    assert json.loads(SNAPSHOT.read_text(encoding="utf-8")) == live, (
        "apps/web/openapi.json is stale: run the one-liner in apps/web/README.md, "
        "then `npm run gen:api` and `npm run lint` inside apps/web"
    )
