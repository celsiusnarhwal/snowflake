FROM cgr.dev/chainguard/wolfi-base

LABEL org.opencontainers.image.authors="celsius narhwal <hello@celsiusnarhwal.dev>"

ENV PATH="/app/.venv/bin:${PATH}"

USER nonroot

WORKDIR /app/

COPY --from=astral/uv:0.13 uv uvx /bin/

ARG PDM_BUILD_SCM_VERSION
COPY pyproject.toml uv.lock /app/
RUN uv sync

COPY . /app/

HEALTHCHECK CMD httpx http://localhost:8000/health

EXPOSE 8000

CMD ["uv", "run", "--quiet", "uvicorn", "--host", "", "--port", "8000", "snowflake.app:app"]