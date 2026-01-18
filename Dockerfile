FROM ghcr.io/astral-sh/uv:0.6-debian

ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

WORKDIR /app/

COPY pyproject.toml uv.lock /app/
RUN uv sync

COPY . /app/

HEALTHCHECK CMD curl -fs localhost:${UVICORN_PORT}/health

CMD ["uv", "run", "uvicorn", "snowflake.app:app"]