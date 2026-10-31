# Ripple service image: one image, two commands (api, worker). ADR-0011 (uv), ADR-0022.
# Build:  docker build -f infra/Dockerfile -t ripple:local .
# Run:    docker run --env-file .env ripple:local api | worker
# The trained link finder (RIPPLE_LINKER=trained, ADR-0128) needs torch; build with
#   --build-arg SYNC_GROUPS="--group linkfinder"   to include it. The default image
# serves the LLM linker and stays free of the CPU torch wheels (ADR-0125 point 4).

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/
WORKDIR /app

FROM base AS deps
ARG SYNC_GROUPS="--no-group linkfinder"
COPY pyproject.toml uv.lock ./
# Install dependencies only (no project) so this layer caches across code changes.
RUN uv sync --locked --no-dev $SYNC_GROUPS --no-install-project

FROM base AS runtime
ARG SYNC_GROUPS="--no-group linkfinder"
RUN useradd --create-home --uid 10001 ripple
COPY --from=deps /app/.venv /app/.venv
COPY pyproject.toml uv.lock alembic.ini README.md ./
COPY src ./src
COPY infra/migrations ./infra/migrations
COPY config ./config
RUN uv sync --locked --no-dev $SYNC_GROUPS
ENV PATH="/app/.venv/bin:$PATH"
USER ripple
COPY infra/entrypoint.sh /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["api"]
