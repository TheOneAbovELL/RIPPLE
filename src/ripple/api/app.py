"""App factory (ADR-0041): `create_app(services)` is the only way to build the API.

No module-level app, no settings read here; tests pass fakes, production passes what
`ripple.api.wiring` built. Routers are grouped by OpenAPI tag so the dashboard's
generated client mirrors the product's surfaces.
"""

from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ripple.api.errors import install_error_handlers
from ripple.api.health import Readiness
from ripple.api.health import router as health_router
from ripple.api.logging import RequestIdMiddleware
from ripple.api.middleware import (
    DEFAULT_MAX_BODY_BYTES,
    BodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from ripple.api.ratelimit import RateLimitGuard, enforce_rate_limit
from ripple.api.routers import (
    events,
    feedback,
    graph,
    me,
    memories,
    openings,
    questions,
    recommendations,
    resume,
    statements,
    vocabulary,
)
from ripple.api.services import Services

API_TITLE = "Ripple"
API_VERSION = "0.0.1"

TAGS = [
    {"name": "statements", "description": "Write flow: a statement becomes a memory and ripples."},
    {"name": "memories", "description": "Inspector: see, explain, edit and forget beliefs."},
    {"name": "questions", "description": "Questions the resolver parked for the user (FR-7)."},
    {"name": "resume", "description": "Resume upload and candidate confirmation (FR-1, I5)."},
    {"name": "openings", "description": "Pasted or forwarded job descriptions (FR-2)."},
    {"name": "recommendations", "description": "Ranked openings for the user."},
    {"name": "me", "description": "Identity, Telegram linking, export and deletion (FR-15)."},
    {
        "name": "feedback",
        "description": "Pilot feedback on recommendations and questions (ADR-0105).",
    },
]


def create_app(
    services: Services,
    *,
    rate_limit: RateLimitGuard | None = None,
    readiness: Readiness | None = None,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
    cors_origins: Sequence[str] = (),
) -> FastAPI:
    # No slash redirects: behind Caddy's `handle_path /api/*` a redirect would drop the
    # /api prefix and point the client at the dashboard (ADR-0029).
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        openapi_tags=TAGS,
        lifespan=lifespan,
        redirect_slashes=False,
    )
    app.state.services = services
    # Hardening (ADR-0098): None means no write-rate limiting / no readiness probes,
    # which is what tests and a bare development run want.
    app.state.rate_limit = rate_limit
    app.state.readiness = readiness
    # Starlette runs the last-added middleware first. The body cap sits inside the
    # security headers so its own 413 carries them too.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware)
    if cors_origins:
        # Development only (`next dev` on another port); production is same-origin
        # behind Caddy and passes no origins (ADR-0029).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        )
    app.add_middleware(RequestIdMiddleware)  # outermost: every log line below has the id
    install_error_handlers(app)
    app.include_router(health_router)
    for router in (
        statements.router,
        memories.router,
        questions.router,
        resume.router,
        openings.router,
        recommendations.router,
        me.router,
        graph.router,
        vocabulary.router,
        feedback.router,
        events.router,
    ):
        app.include_router(router, dependencies=[Depends(enforce_rate_limit)])
    return app


def create_production_app() -> FastAPI:
    """What infra/entrypoint.sh runs: `uvicorn ripple.api.app:create_production_app --factory`.

    Imported lazily because wiring imports this module for `create_app`.
    """
    from ripple.api.wiring import app_from_env

    return app_from_env()
