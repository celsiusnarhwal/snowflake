FROM ghcr.io/astral-sh/uv:0.9-debian

LABEL org.opencontainers.image.authors="celsius narhwal <hello@celsiusnarhwal.dev>"

ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

WORKDIR /app/

COPY pyproject.toml uv.lock /app/
RUN uv sync

COPY . /app/

HEALTHCHECK CMD curl -fs localhost:${UVICORN_PORT}/health

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "snowflake.app:app"]