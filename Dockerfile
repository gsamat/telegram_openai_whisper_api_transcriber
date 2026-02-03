ARG PYTHON_VERSION=3.14
ARG RELEASE=dev
#
# Build virtual environment with dependencies
# https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile
#
FROM python:${PYTHON_VERSION}-slim-bookworm AS deps-compile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

WORKDIR /src

COPY pyproject.toml uv.lock /src/
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev


FROM python:${PYTHON_VERSION}-slim-bookworm AS base
LABEL maintainer="fedor@borshev.com"
RUN apt-get update \
 && apt-get -y --no-install-recommends install libmagic1 \
 && rm -rf /var/lib/apt/lists/*

ENV BOT_ENV=production
ENV RELEASE=${RELEASE}

COPY --from=deps-compile --chown=nobody:nogroup /src/.venv /src/.venv
ENV PATH="/src/.venv/bin:$PATH"
WORKDIR /
COPY src /src

#
# Bot image
#
FROM base
WORKDIR /src

# Create data directory for SQLite persistence
RUN mkdir -p /data && chown nobody:nogroup /data
ENV DATABASE_PATH=/data/billing.db
VOLUME /data

USER nobody

CMD ["python", "-m", "bot"]
