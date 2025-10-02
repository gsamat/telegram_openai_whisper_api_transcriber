FROM python:3.12-slim-trixie

# lint hint:
# docker run --rm -i hadolint/hadolint < Dockerfile
#
# rules:
# https://github.com/hadolint/hadolint?tab=readme-ov-file#rules

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY src/ src/

CMD ["uv", "run", "src/goodsecretarybot.py"]
