# syntax=docker/dockerfile:1.7
FROM python:3.14.7-slim-bookworm AS builder

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY pyproject.toml requirements.lock ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --requirement requirements.lock
COPY src ./src
RUN /opt/venv/bin/pip install --no-deps --force-reinstall .

FROM python:3.14.7-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 florabase \
    && useradd --system --uid 10001 --gid florabase --home-dir /app florabase

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

USER florabase
EXPOSE 8000
CMD ["uvicorn", "florabase.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--no-proxy-headers"]

FROM builder AS development
COPY requirements-dev.lock ./
RUN /opt/venv/bin/pip install --requirement requirements-dev.lock
ENV PYTHONPATH=/app/src
WORKDIR /app
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY tests ./tests
COPY pyproject.toml ./
CMD ["uvicorn", "florabase.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
