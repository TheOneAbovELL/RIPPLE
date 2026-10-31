"""The whole product on one local origin with one command (ADR-0132, ADR-0133).

    uv run python -m tools.local_run [--seed-demo] [--port 8765] [--fresh]

Starts embedded Postgres (ADR-0115), migrates, builds or reuses the dashboard export,
creates a user and prints the token once, then serves the API at /api and the
dashboard at /, like Caddy does in production, with Caddy's security headers. The API
is the production wiring (`build_services`) unchanged; what needs ANTHROPIC_API_KEY or
TELEGRAM_BOT_TOKEN is printed at start-up.

`--seed-demo` writes a demo student through the real write paths (Intake, the opening
recorder, the ripple engine): profile facts, three openings with derived beliefs, a
CGPA change that ripples, and a CGPA-scale correction the rules refuse to guess about,
which parks questions. The seed's resolver falls back to asking the student instead of
the model, so the demo is the same with or without a key and costs nothing.
"""

import argparse
import asyncio
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.routing import Mount
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ripple.api.adapters import OpeningRecorderAdapter
from ripple.api.admin import create_user
from ripple.core.change_detection import ChangeClassification
from ripple.core.clock import Clock
from ripple.core.errors import InvalidObjectError
from ripple.core.intake import Intake
from ripple.core.models import ChangeEvent, DecisionAction, Memory, StructuredFact
from ripple.core.resolver import Resolution, ResolutionContext, ResolverChain
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.domains.jobs.derive import ProfileDerivationObserver
from ripple.domains.jobs.linker import JobsStructureLinker
from ripple.domains.jobs.profile import profile_statement
from ripple.domains.jobs.rules import jobs_rules
from ripple.domains.jobs.vocabulary import (
    MULTI_VALUED_PROFILE_ATTRIBUTES,
    PERMANENT_PROFILE_FACTS,
    OpeningAttribute,
    ParsedField,
    ParsedOpening,
    ProfileAttribute,
    TextSpan,
    jobs_registry,
)
from ripple.linking.composite import StructuredFirstLinker
from ripple.linking.rules import RuleLinker

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "apps" / "web"
DEFAULT_PORT = 8765
DEFAULT_DATA = Path.home() / ".ripple" / "pgdata"
ENV_API_KEY = "ANTHROPIC_API_KEY"
ENV_TELEGRAM = "TELEGRAM_BOT_TOKEN"

# The Caddyfile's header block (infra/Caddyfile, ADR-0029) minus HSTS, which a plain-HTTP
# localhost must not send. A CSP violation in the export shows up here first.
SECURITY_HEADERS: Mapping[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"
    ),
}

# ---- the dashboard export ---------------------------------------------------------------


def web_sources(web_dir: Path) -> list[Path]:
    """Everything a rebuild of the export depends on."""
    sources = [p for p in (web_dir / "src").rglob("*") if p.is_file()]
    if (web_dir / "public").exists():
        sources += [p for p in (web_dir / "public").rglob("*") if p.is_file()]
    for name in (
        "openapi.json",
        "package.json",
        "package-lock.json",
        "next.config.ts",
        "tsconfig.json",
    ):
        if (web_dir / name).exists():
            sources.append(web_dir / name)
    return sources


def export_is_current(out_dir: Path, sources: Sequence[Path]) -> bool:
    """True when out/index.html exists and is newer than every source file."""
    index = out_dir / "index.html"
    if not index.exists():
        return False
    built = index.stat().st_mtime
    return all(source.stat().st_mtime <= built for source in sources)


Runner = Callable[..., Any]


def build_dashboard(web_dir: Path, *, force: bool, run: Runner = subprocess.run) -> Path:
    """Reuse apps/web/out when it is current; otherwise `npm ci` (if needed) and build."""
    out_dir = web_dir / "out"
    if not force and export_is_current(out_dir, web_sources(web_dir)):
        print(f"Dashboard: reusing the export in {out_dir}", flush=True)
        return out_dir
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit(
            "npm was not found; install Node 22, or pass --no-web to serve the API only"
        )
    # The default API base ("/api") is what this server mounts; a value left in the
    # environment for `next dev` would point the export at another origin.
    env = {k: v for k, v in os.environ.items() if k != "NEXT_PUBLIC_RIPPLE_API_BASE"}
    if not (web_dir / "node_modules").exists():
        print("Dashboard: installing packages (npm ci)...", flush=True)
        run([npm, "ci"], cwd=web_dir, env=env, check=True)
    print("Dashboard: building the static export (npm run build)...", flush=True)
    run([npm, "run", "build"], cwd=web_dir, env=env, check=True)
    return out_dir


# ---- one origin: /api to the API, everything else to the export -----------------------


class ExportFiles:
    """Caddy's `try_files {path} {path}/ /index.html` over the static export."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def resolve(self, path: str) -> Path:
        relative = path.lstrip("/")
        for candidate in (relative, f"{relative}/index.html".lstrip("/")):
            target = (self._root / candidate).resolve()
            # A path that climbs out of the export (../) is never served.
            if target.is_relative_to(self._root) and target.is_file():
                return target
        return self._root / "index.html"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        response: Response
        if scope["method"] not in ("GET", "HEAD"):
            response = PlainTextResponse("method not allowed", status_code=405)
        else:
            target = self.resolve(scope["path"])
            response = (
                FileResponse(target)
                if target.is_file()
                else PlainTextResponse("dashboard export missing", status_code=404)
            )
        await response(scope, receive, send)


class SecurityHeaders:
    """Adds the Caddy headers to every response that does not set them itself."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                present = {name.lower() for name, _ in message.get("headers", [])}
                extra = [
                    (name.lower().encode(), value.encode())
                    for name, value in SECURITY_HEADERS.items()
                    if name.lower().encode() not in present
                ]
                message["headers"] = [*message.get("headers", []), *extra]
            await send(message)

        await self._app(scope, receive, with_headers)


def build_site(api: ASGIApp, out_dir: Path | None) -> Starlette:
    """The API under /api (prefix stripped, as Caddy's handle_path does) next to the export.

    The API's own lifespan runs inside the site's, since Starlette does not start the
    lifespan of a mounted app.
    """
    static: ASGIApp = (
        ExportFiles(out_dir)
        if out_dir is not None
        else PlainTextResponse("API only (--no-web): the API is at /api")
    )

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        context = getattr(getattr(api, "router", None), "lifespan_context", None)
        if context is None:
            yield
            return
        async with context(api):
            yield

    site = Starlette(routes=[Mount("/api", app=api), Mount("/", app=static)], lifespan=lifespan)
    site.add_middleware(SecurityHeaders)
    return site


# ---- the demo seed ----------------------------------------------------------------------


class AskTheStudent:
    """The seed's resolver fallback: when every jobs rule declines, ask, never guess.

    Production falls back to the LLM resolver, which may also ask; asking is the one
    answer that is safe without a model (ADR-0133).
    """

    async def resolve(self, context: ResolutionContext) -> Resolution:
        return Resolution(
            action=DecisionAction.ASK,
            reason=(
                "the jobs rules cannot decide this case and no language model was used, "
                "so Ripple asks instead of guessing"
            ),
            question=(
                f"After “{context.trigger.content}”, Ripple could not re-check "
                f"“{context.memory.content}” by its rules. Does it still hold?"
            ),
            evidence_refs=(context.trigger.id,),
        )


class StructuredFactsOnly:
    """The seed's change detector: it writes permanent structured facts only, which
    Intake classifies without a detector (ADR-0116); anything else is a seed bug."""

    async def classify(
        self, content: str, structured: StructuredFact | None, candidates: Sequence[Memory]
    ) -> ChangeClassification:
        raise InvalidObjectError(
            f"the demo seed writes structured permanent facts only: {content!r}"
        )


@dataclass
class DemoReport:
    user_id: str
    facts: int = 0
    openings: list[str] = field(default_factory=list)
    events: list[ChangeEvent] = field(default_factory=list)

    @property
    def asked(self) -> int:
        return sum(1 for e in self.events for d in e.decisions if d.action is DecisionAction.ASK)

    @property
    def updated(self) -> int:
        return sum(1 for e in self.events for d in e.decisions if d.action is DecisionAction.UPDATE)


def seed_runner(store: Store, clock: Clock) -> tuple[RippleRunner, Intake]:
    """Production's components with the three model seams replaced (ADR-0133): the
    resolver fallback asks, the prose linker is RuleLinker, the detector refuses."""
    derivation = ProfileDerivationObserver(store, clock)
    runner = RippleRunner(
        store,
        ResolverChain(jobs_rules(), fallback=AskTheStudent()),
        clock,
        observers=(derivation,),
    )
    derivation.attach(runner)
    linker = StructuredFirstLinker([JobsStructureLinker(), RuleLinker()], RuleLinker())
    intake = Intake(
        store,
        clock,
        jobs_registry(),
        linker,
        StructuredFactsOnly(),
        runner,
        multi_valued_attributes=MULTI_VALUED_PROFILE_ATTRIBUTES,
        permanent_facts=PERMANENT_PROFILE_FACTS,
    )
    return runner, intake


PROFILE: Sequence[tuple[ProfileAttribute, str | int | float, str]] = (
    (
        ProfileAttribute.BRANCH,
        "Computer Science and Engineering",
        "I study Computer Science and Engineering",
    ),
    (ProfileAttribute.BATCH, 2028, "I graduate with the 2028 batch"),
    (ProfileAttribute.CGPA, 8.1, "My CGPA is 8.1"),
    (ProfileAttribute.SKILL, "Python", "I know Python"),
    (ProfileAttribute.SKILL, "SQL", "I know SQL"),
    (ProfileAttribute.SKILL, "React", "I know React"),
    (
        ProfileAttribute.PROJECT,
        "a placement-notice tracker in Django",
        "I built a placement-notice tracker in Django",
    ),
)


@dataclass(frozen=True)
class DemoOpening:
    slug: str
    text: str
    summary: str
    # (attribute, value, the exact words in `text` it was read from)
    fields: Sequence[tuple[OpeningAttribute, str | int | float, str]]


IST = timezone(timedelta(hours=5, minutes=30), "IST")  # the pilot's zone; tzdata-free


def _deadline_words(moment: datetime) -> str:
    """ "14 November 2026, 11:59 PM IST", the way a placement notice writes it."""
    return moment.strftime("%d %B %Y, %I:%M %p IST").lstrip("0")


def _closing(now: datetime, days: int, hour: int, minute: int) -> datetime:
    return (
        (now + timedelta(days=days))
        .astimezone(IST)
        .replace(hour=hour, minute=minute, second=0, microsecond=0)
    )


def demo_openings(now: datetime) -> list[DemoOpening]:
    """Three realistic JDs, dated from `now` so their deadlines stay in the future."""
    acme_close = _closing(now, 9, 23, 59)
    beta_close = _closing(now, 3, 18, 0)
    gamma_close = _closing(now, 16, 17, 0)
    acme = (
        "Acme Robotics is hiring a Software Development Engineer Intern for summer 2027.\n"
        "Location: Bengaluru (hybrid).\n"
        "Eligibility: B.Tech students of the 2028 batch with a CGPA of 7.0 and above.\n"
        "Skills: Python and React; SQL is a plus.\n"
        f"Apply by {_deadline_words(acme_close)} through the placement cell portal."
    )
    beta = (
        "Beta Analytics: Data Science Intern (6 months, stipend)\n"
        "Location: Pune\n"
        "Open to the 2028 batch, minimum CGPA 8.5, no active backlogs.\n"
        "We look for strong SQL and Python; exposure to statistics helps.\n"
        f"Last date to apply: {_deadline_words(beta_close)}."
    )
    gamma = (
        "Gamma Labs, Machine Learning Intern, remote.\n"
        "Open to students graduating in 2028.\n"
        "Required: Python and PyTorch.\n"
        f"Applications close on {_deadline_words(gamma_close)}."
    )
    return [
        DemoOpening(
            "acme",
            acme,
            "Software Development Engineer Intern at Acme Robotics",
            (
                (
                    OpeningAttribute.TITLE,
                    "Software Development Engineer Intern",
                    "Software Development Engineer Intern",
                ),
                (OpeningAttribute.COMPANY, "Acme Robotics", "Acme Robotics"),
                (OpeningAttribute.ROLE_TYPE, "internship", "Intern"),
                (OpeningAttribute.LOCATION, "Bengaluru", "Bengaluru (hybrid)"),
                (OpeningAttribute.BATCH, 2028, "2028 batch"),
                (OpeningAttribute.CGPA_CUTOFF, 7.0, "CGPA of 7.0 and above"),
                (OpeningAttribute.REQUIRED_SKILL, "Python", "Python"),
                (OpeningAttribute.REQUIRED_SKILL, "React", "React"),
                (OpeningAttribute.DEADLINE, acme_close.isoformat(), _deadline_words(acme_close)),
            ),
        ),
        DemoOpening(
            "beta",
            beta,
            "Data Science Intern at Beta Analytics",
            (
                (OpeningAttribute.TITLE, "Data Science Intern", "Data Science Intern"),
                (OpeningAttribute.COMPANY, "Beta Analytics", "Beta Analytics"),
                (OpeningAttribute.ROLE_TYPE, "internship", "Intern"),
                (OpeningAttribute.LOCATION, "Pune", "Pune"),
                (OpeningAttribute.BATCH, 2028, "2028 batch"),
                (OpeningAttribute.CGPA_CUTOFF, 8.5, "minimum CGPA 8.5"),
                (OpeningAttribute.REQUIRED_SKILL, "SQL", "SQL"),
                (OpeningAttribute.REQUIRED_SKILL, "Python", "Python"),
                (OpeningAttribute.DEADLINE, beta_close.isoformat(), _deadline_words(beta_close)),
            ),
        ),
        DemoOpening(
            "gamma",
            gamma,
            "Machine Learning Intern at Gamma Labs",
            (
                (OpeningAttribute.TITLE, "Machine Learning Intern", "Machine Learning Intern"),
                (OpeningAttribute.COMPANY, "Gamma Labs", "Gamma Labs"),
                (OpeningAttribute.ROLE_TYPE, "internship", "Intern"),
                (OpeningAttribute.LOCATION, "remote", "remote"),
                (OpeningAttribute.BATCH, 2028, "2028"),
                (OpeningAttribute.REQUIRED_SKILL, "Python", "Python"),
                (OpeningAttribute.REQUIRED_SKILL, "PyTorch", "PyTorch"),
                (OpeningAttribute.DEADLINE, gamma_close.isoformat(), _deadline_words(gamma_close)),
            ),
        ),
    ]


def parsed_opening(opening: DemoOpening, source_ref: str) -> ParsedOpening:
    """The parser's output shape, with spans located in the text (FR-2: exact words)."""
    fields: list[ParsedField] = []
    for attribute, value, words in opening.fields:
        start = opening.text.index(words)
        span = TextSpan(start=start, end=start + len(words), text=words)
        fields.append(ParsedField(attribute=attribute, value=value, span=span))
    return ParsedOpening(
        source_ref=source_ref, raw_text=opening.text, fields=tuple(fields), summary=opening.summary
    )


async def seed_demo(store: Store, clock: Clock, user_id: str) -> DemoReport:
    """Write the demo student through Intake, the opening recorder and the engine."""
    runner, intake = seed_runner(store, clock)
    recorder = OpeningRecorderAdapter(store, clock, runner)
    report = DemoReport(user_id=user_id)

    for attribute, value, words in PROFILE:
        result = await intake.ingest(profile_statement(user_id, attribute, value, content=words))
        report.facts += 1
        if result.event is not None:
            report.events.append(result.event)

    for opening in demo_openings(clock.now()):
        written = await recorder.record(
            user_id, parsed_opening(opening, f"paste:demo-{opening.slug}")
        )
        report.openings.append(written.opening_memory_id)

    # The ripple to look at first: the CGPA rises past Beta's cutoff, so its eligibility
    # is updated while Acme's (7.0) is re-checked and kept.
    for attribute, value, words in (
        (ProfileAttribute.CGPA, 8.6, "My CGPA is 8.6 after the sixth-semester results"),
        # The ask path (ADR-0034): a 4-point scale cannot be compared with ten-point
        # cutoffs, so the rules decline and the student is asked, not second-guessed.
        (ProfileAttribute.CGPA_SCALE, 4, "My college reports CGPA on a 4-point scale"),
    ):
        result = await intake.ingest(profile_statement(user_id, attribute, value, content=words))
        if result.event is not None:
            report.events.append(result.event)
    return report


# ---- start-up banner --------------------------------------------------------------------

NEEDS_MODEL = (
    "reading a resume PDF (Resume page)",
    "reading a pasted job description (Add an opening)",
    "free-text statements without a picked fact, and facts that can lapse",
    "a ripple the rules cannot decide (it stays open until a model is available)",
    "the Telegram conversation agent",
)
WORKS_WITHOUT = (
    "profile facts through 'This changes one profile fact' (deterministic, ADR-0116)",
    "beliefs, history, questions and answers, recommendations, the map",
    "Telegram link codes, export and delete-everything",
)


def banner(url: str, token: str, env: Mapping[str, str], *, seeded: DemoReport | None) -> str:
    has_key = bool(env.get(ENV_API_KEY, "").strip())
    has_bot = bool(env.get(ENV_TELEGRAM, "").strip())
    lines = [
        "",
        "Ripple is running.",
        f"  Dashboard: {url}/",
        f"  API:       {url}/api  (health: {url}/api/healthz)",
        f"  Token:     {token}",
        "  Paste the token on the sign-in page. It is shown once; a new run makes a new user.",
        "",
    ]
    if seeded is not None:
        lines += [
            f"Demo student seeded: {seeded.facts} profile facts, {len(seeded.openings)} openings,",
            f"  {len(seeded.events)} ripples ({seeded.updated} beliefs updated, "
            f"{seeded.asked} questions parked). Open Home to see them.",
            "",
        ]
    if has_key:
        lines.append(f"{ENV_API_KEY} is set: model-backed features are on.")
    else:
        lines.append(f"{ENV_API_KEY} is not set. These need it and answer 503 until it is:")
        lines += [f"  - {item}" for item in NEEDS_MODEL]
        lines.append("  Works without it:")
        lines += [f"  - {item}" for item in WORKS_WITHOUT]
    lines.append("")
    if has_bot:
        lines.append(
            f"{ENV_TELEGRAM} is set. The webhook is not mounted locally; for the bot run "
            "`uv run python -m ripple.worker.telegram_poll` in another terminal."
        )
    else:
        lines.append(
            f"{ENV_TELEGRAM} is not set: no bot. Digests and alerts can still be previewed with "
            "`uv run python -m ripple.worker.run_once daily_digest` (prints, sends nothing)."
        )
    lines += ["", "Press Ctrl+C to stop. Postgres keeps its data unless --fresh was given.", ""]
    return "\n".join(lines)


# ---- main -------------------------------------------------------------------------------


def migrate(database_url: str) -> None:
    env = dict(os.environ, DATABASE_URL=database_url)
    print("Database: migrating to head (alembic upgrade head)...", flush=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True
    )


async def serve(args: argparse.Namespace, database_url: str, out_dir: Path | None) -> None:
    import uvicorn

    from ripple.api.app import create_app
    from ripple.api.logging import configure_logging
    from ripple.api.wiring import (
        Settings,
        api_lifespan,
        build_services,
        rate_limit_guard,
        readiness_probes,
    )
    from ripple.storage.engine import engine_from_url

    env = dict(os.environ, DATABASE_URL=database_url)
    env.setdefault("RIPPLE_LOG_JSON", "false")  # readable lines in a terminal
    settings = Settings.from_env(env)
    configure_logging(settings.log_level, json_lines=settings.log_json)
    engine = engine_from_url(database_url)
    services = build_services(settings, engine=engine)
    api = create_app(
        services,
        rate_limit=rate_limit_guard(settings, services.clock),
        readiness=readiness_probes(settings, engine),
        # No webhook locally: the bot runs by long-poll (ripple.worker.telegram_poll).
        lifespan=api_lifespan(settings, services, env, webhook_secret=None),
    )
    # Everything below runs on the server's loop: the engine's pooled connections belong
    # to the loop that opened them.
    name = args.name or ("Asha Verma" if args.seed_demo else "Local student")
    try:
        user, token = await create_user(services.user_store, services.clock, name)
        seeded = (
            await seed_demo(services.store, services.clock, user.id) if args.seed_demo else None
        )
        url = f"http://127.0.0.1:{args.port}"
        print(banner(url, token, env, seeded=seeded), flush=True)
        config = uvicorn.Config(
            build_site(api, out_dir),
            host="127.0.0.1",
            port=args.port,
            loop="none",
            log_level="info",
        )
        await uvicorn.Server(config).serve()
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.local_run",
        description="Run the whole product (API and dashboard) on one local origin.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Postgres data directory")
    parser.add_argument(
        "--fresh", action="store_true", help="a throwaway database, deleted at exit"
    )
    parser.add_argument("--seed-demo", action="store_true", help="write a demo student")
    parser.add_argument("--name", default=None, help="display name of the new user")
    parser.add_argument("--rebuild-web", action="store_true", help="rebuild the dashboard export")
    parser.add_argument("--no-web", action="store_true", help="serve the API only")
    args = parser.parse_args(argv)

    from ripple.storage.loop import use_selector_event_loop
    from tools.embedded_pg import start

    use_selector_event_loop()  # psycopg async on Windows (ADR-0115)
    if args.fresh:
        data = Path(tempfile.mkdtemp(prefix="ripple-local-"))
        database_url = start(data, cleanup="delete")
    else:
        args.data.mkdir(parents=True, exist_ok=True)
        database_url = start(args.data, cleanup=None)
    print(f"Database: embedded Postgres at {database_url}", flush=True)
    migrate(database_url)
    out_dir = None if args.no_web else build_dashboard(WEB_DIR, force=args.rebuild_web)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve(args, database_url, out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
