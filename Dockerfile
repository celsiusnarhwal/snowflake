FROM redis:latest AS redis

FROM ghcr.io/astral-sh/uv:0.6-debian

ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

WORKDIR /app/

COPY --from=redis /usr/local/bin/redis-server /usr/local/bin/redis-server

COPY pyproject.toml uv.lock /app/
RUN uv sync

COPY . /app/

CMD ["sh", "-c", "redis-server --daemonize yes && uv run uvicorn snowflake.app:app"]