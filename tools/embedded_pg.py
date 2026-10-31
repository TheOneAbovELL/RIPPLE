"""Real Postgres with pgvector on a developer machine, without Docker (ADR-0115).

    uv run python -m tools.embedded_pg test      # start Postgres, run the slow suite, stop
    uv run python -m tools.embedded_pg serve     # start Postgres, print DATABASE_URL, wait

pgserver ships Postgres and pgvector binaries for Windows, macOS and Linux as a wheel.
The data directory lives under the user's cache (or --data), so `serve` keeps its data
between runs; `test` always uses a fresh temporary directory and a fresh database.
Production and CI keep using the pgvector container (ADR-0004, ADR-0029).
"""

import argparse
import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pgserver.postgres_server import get_server

REPO_ROOT = Path(__file__).resolve().parents[1]
DATABASE = "ripple"


def start(data_dir: Path, *, cleanup: str | None) -> str:
    """Start (or attach to) the server in `data_dir`; return a SQLAlchemy psycopg URL."""
    server = get_server(str(data_dir), cleanup_mode=cleanup)
    exists = server.psql(f"SELECT 1 FROM pg_database WHERE datname = '{DATABASE}';")
    if "1 row" not in exists:
        server.psql(f"CREATE DATABASE {DATABASE};")
    base = server.get_uri().rsplit("/", 1)[0]
    return base.replace("postgresql://", "postgresql+psycopg://", 1) + f"/{DATABASE}"


def run_slow_suite(extra: list[str]) -> int:
    # "delete" lets pgserver stop the server and remove the directory itself; Windows
    # cannot remove files a running server still holds, so no TemporaryDirectory here.
    data = Path(tempfile.mkdtemp(prefix="ripple-pg-"))
    url = start(data, cleanup="delete")
    env = dict(os.environ, TEST_DATABASE_URL=url, DATABASE_URL=url)
    print(f"TEST_DATABASE_URL={url}", flush=True)
    return subprocess.call(
        [sys.executable, "-m", "pytest", "-m", "slow", *extra], cwd=REPO_ROOT, env=env
    )


def serve(data_dir: Path) -> int:
    url = start(data_dir, cleanup=None)  # None: the server outlives this process
    print(f"DATABASE_URL={url}", flush=True)
    print("Postgres is running; press Ctrl+C to leave it (it keeps running).", flush=True)
    with contextlib.suppress(EOFError, KeyboardInterrupt):
        input()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.embedded_pg")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test", help="run the slow suite against a fresh embedded Postgres")
    run = sub.add_parser("serve", help="start a persistent embedded Postgres")
    run.add_argument("--data", type=Path, default=Path.home() / ".ripple" / "pgdata")
    # Anything after the subcommand that argparse does not know goes to pytest.
    args, pytest_args = parser.parse_known_args(argv)
    if args.command == "test":
        return run_slow_suite(pytest_args)
    args.data.mkdir(parents=True, exist_ok=True)
    return serve(args.data)


if __name__ == "__main__":
    raise SystemExit(main())
