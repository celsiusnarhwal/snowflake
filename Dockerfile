FROM ghcr.io/astral-sh/uv:0.9-debian

LABEL org.opencontainers.image.authors="celsius narhwal <hello@celsiusnarhwal.dev>"

ENV PATH="/app/.venv/bin:${PATH}"

WORKDIR /app/

COPY pyproject.toml uv.lock /app/
RUN uv sync

COPY . /app/

HEALTHCHECK CMD curl -fs localhost:8000/health

EXPOSE 8000

CMD ["uv", "run", "--quiet", "uvicorn", "--host", "", "--port", "8000", "snowflake.app:app"]