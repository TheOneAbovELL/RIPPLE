"""Weekly pilot report: `python -m ripple.pilot.report --week 2026-W45` (ADR-0106).

Reads the store (ChangeEvents and version chains), the delivery log and the feedback
table for one ISO week in UTC, computes what `ripple.pilot.metrics` can, and writes
metrics.json, report.md and config.json (I8) into results/pilot/<week>/, or into
results/pilot/raw/<week>/ (gitignored) when fewer than MIN_PUBLISHABLE_COHORT students
were active. It refuses to overwrite an existing week folder or to report a week that
has not ended unless asked, so a number once quoted keeps its file.

The report holds aggregates only: no user id, display name, note or memory content
(consent: "no student is identifiable in any report"). Notes stay in the database.
"""

import argparse
import asyncio
import json
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from ripple.core.errors import ConfigurationError
from ripple.core.models import ChangeEvent, Memory
from ripple.core.store import MemoryNotFoundError
from ripple.pilot.deliveries import DeliveryReader, PostgresDeliveryReader
from ripple.pilot.metrics import TBD, week_metrics
from ripple.pilot.weeks import Week, parse_week
from ripple.storage.engine import ENV_VAR, database_url, engine_from_url
from ripple.storage.feedback import RECOMMENDATION_KINDS, Feedback, PostgresFeedbackStore
from ripple.storage.postgres import PostgresStore
from ripple.storage.users import PostgresUserStore

REPORT_VERSION = "pilot-report v1"
DEFAULT_RESULTS_DIR = Path("results") / "pilot"
UNPUBLISHED_SUBDIR = "raw"  # results/*/raw/ is gitignored
# Earlier than any pilot row; the share counts a save made in any week before the end.
HISTORY_START = datetime(2026, 1, 1, tzinfo=UTC)


class FeedbackReader(Protocol):
    async def feedback_between(self, start: datetime, end: datetime) -> list[Feedback]: ...


class MemoryHistory(Protocol):
    async def change_events_for_user(self, user_id: str) -> list[ChangeEvent]: ...

    async def version_chain(self, memory_id: str) -> list[Memory]: ...


@dataclass(frozen=True)
class PilotSources:
    """Everything the report reads; Postgres in production, fakes in tests."""

    account_ids: Sequence[str]
    history: MemoryHistory
    deliveries: DeliveryReader
    feedback: FeedbackReader
    description: str  # what config.json records as the data source, never a URL


class WeekNotOverError(RuntimeError):
    pass


class ReportExistsError(RuntimeError):
    pass


async def first_versions(history: MemoryHistory, memory_ids: Iterable[str]) -> dict[str, str]:
    """memory id → its first version's id; a forgotten id maps to itself."""
    canonical: dict[str, str] = {}
    for memory_id in sorted(set(memory_ids)):
        try:
            chain = await history.version_chain(memory_id)
        except MemoryNotFoundError:
            continue
        if chain:
            canonical[memory_id] = chain[0].id
    return canonical


async def collect(sources: PilotSources, week: Week) -> dict[str, Any]:
    deliveries = await sources.deliveries.deliveries_between(week.start, week.end)
    feedback = await sources.feedback.feedback_between(HISTORY_START, week.end)
    events: list[ChangeEvent] = []
    for user_id in sources.account_ids:
        events.extend(await sources.history.change_events_for_user(user_id))
    openings = [d.key for d in deliveries if not d.is_digest] + [
        f.target_memory_id for f in feedback if f.kind in RECOMMENDATION_KINDS
    ]
    canonical = await first_versions(sources.history, openings)
    return week_metrics(week, sources.account_ids, deliveries, feedback, events, canonical)


def render_markdown(metrics: dict[str, Any], config: dict[str, Any]) -> str:
    cohort, activity, pilot = metrics["cohort"], metrics["activity"], metrics["pilot_metrics"]
    lines = [
        f"# Pilot report {metrics['week']}",
        f"Window {metrics['window']['start']} to {metrics['window']['end']} (UTC, end "
        f"exclusive). Generated {config['generated_at']} from {config['sources']} at "
        f"{config['code_version']}. Every number below is in metrics.json beside this file.",
        "",
    ]
    if config["partial"]:
        lines += ["**Partial week: generated before the week ended.**", ""]
    if not cohort["publishable"]:
        lines += [
            f"**Not for publication: {cohort['active_users']} active students, fewer than "
            f"{cohort['min_publishable_cohort']}; an aggregate may identify a student.**",
            "",
        ]
    lines += [
        "## Pilot metrics (docs/04)",
        "| Metric | Value | From |",
        "|---|---|---|",
    ]
    for name, metric in pilot.items():
        label = name.replace("_", " ")
        if metric["value"] == TBD:
            lines.append(f"| {label} | {TBD} | {metric['reason']} |")
        else:
            lines.append(
                f"| {label} | {metric['value']} | "
                f"{metric['numerator']} / {metric['denominator']}: {metric['definition']} |"
            )
    alerts = ", ".join(f"{k} {v}" for k, v in activity["alerts_sent"].items()) or "none"
    feedback = ", ".join(f"{k} {v}" for k, v in activity["feedback"].items())
    lines += [
        "",
        "## Activity",
        f"- Students: {cohort['accounts']} accounts, {cohort['active_users']} active "
        "(a delivery, a feedback row, an edit or an answer this week).",
        f"- Digests sent: {activity['digests_sent']}. Alerts sent: {alerts}.",
        f"- Feedback rows: {feedback}.",
        "- Reactions to openings not alerted this week (not in the share): "
        f"{activity['recommendation_reactions_without_alert']}.",
        f"- Questions asked: {activity['questions_asked']}.",
        "",
    ]
    return "\n".join(lines)


def week_dir_for(results_dir: Path, week: Week, *, publishable: bool) -> Path:
    base = results_dir if publishable else results_dir / UNPUBLISHED_SUBDIR
    return base / week.label


def write_report(
    week_dir: Path, metrics: dict[str, Any], config: dict[str, Any], *, overwrite: bool
) -> None:
    config_path = week_dir / "config.json"
    if week_dir.exists():
        if not overwrite:
            raise ReportExistsError(f"{week_dir} exists; pass --overwrite to replace it")
        if config_path.exists():
            # Alert rows move on re-alert, so a regenerated week may differ; keep the
            # trace of the version it replaced.
            previous = json.loads(config_path.read_text(encoding="utf-8"))
            config = {**config, "replaces_generated_at": previous.get("generated_at")}
    week_dir.mkdir(parents=True, exist_ok=True)
    (week_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (week_dir / "report.md").write_text(render_markdown(metrics, config), encoding="utf-8")


async def generate(
    sources: PilotSources,
    week: Week,
    *,
    results_dir: Path,
    now: datetime,
    code_version: str,
    partial: bool = False,
    overwrite: bool = False,
) -> Path:
    if now < week.end and not partial:
        raise WeekNotOverError(f"{week.label} ends {week.end.isoformat()}; pass --partial")
    metrics = await collect(sources, week)
    publishable = bool(metrics["cohort"]["publishable"])
    config = {
        "report_version": REPORT_VERSION,
        "week": week.label,
        "generated_at": now.astimezone(UTC).isoformat(),
        "partial": now < week.end,
        "published": publishable,
        "code_version": code_version,
        "sources": sources.description,
        "metric_definitions": "ADR-0106; docs/pilot/metrics.md",
    }
    week_dir = week_dir_for(results_dir, week, publishable=publishable)
    write_report(week_dir, metrics, config, overwrite=overwrite)
    return week_dir


def git_short_sha(repo: Path) -> str:
    """HEAD's short sha, "-dirty" when the tree differs, "uncommitted" with no commits;
    the same rule as bench.run, which src/ cannot import."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"
    if not head:
        return "uncommitted"
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    )
    return f"{head}-dirty" if status.stdout.strip() else head


async def _postgres_run(args: argparse.Namespace, now: datetime, code_version: str) -> Path:
    url = database_url()
    if url is None:
        raise ConfigurationError(f"{ENV_VAR} is not set; the pilot report reads the database")
    engine = engine_from_url(url)
    try:
        users = await PostgresUserStore(engine).list_users()
        sources = PilotSources(
            account_ids=[u.id for u in users],
            history=PostgresStore(engine),
            deliveries=PostgresDeliveryReader(engine),
            feedback=PostgresFeedbackStore(engine),
            description="postgres",
        )
        return await generate(
            sources,
            parse_week(args.week),
            results_dir=args.results_dir,
            now=now,
            code_version=code_version,
            partial=args.partial,
            overwrite=args.overwrite,
        )
    finally:
        await engine.dispose()


def _week_arg(value: str) -> str:
    try:
        parse_week(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m ripple.pilot.report", description=__doc__)
    parser.add_argument("--week", required=True, type=_week_arg, help="ISO week, e.g. 2026-W45")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--partial", action="store_true", help="allow a week not yet over")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing week")
    parser.add_argument(
        "--code-version",
        help="what config.json records as the code version; default: the git short sha "
        "(pass the image tag inside a container, which has no .git)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    # Blocking subprocess calls stay outside the event loop (.claude/rules/python.md).
    code_version = args.code_version or git_short_sha(Path.cwd())
    try:
        week_dir = asyncio.run(_postgres_run(args, datetime.now(tz=UTC), code_version))
    except (ConfigurationError, WeekNotOverError, ReportExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(week_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
