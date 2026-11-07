# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM python:3.14-slim-bookworm@sha256:516b51cb9db2ef061e465c803e50f64361b82cefd91e525b889b967b83e83527 AS development-builder

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY pyproject.toml requirements.lock ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --require-hashes --requirement requirements.lock
COPY src ./src
RUN /opt/venv/bin/pip install --no-deps --force-reinstall .

FROM python:3.14-alpine@sha256:eb2c62658b8d51bff0acc408504b76521d02030de56a8a3c1e830083e89b89d2 AS builder

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY pyproject.toml requirements.lock ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --only-binary=:all: --require-hashes --requirement requirements.lock
COPY src ./src
RUN /opt/venv/bin/pip install --no-deps --force-reinstall .

FROM python:3.14-alpine@sha256:eb2c62658b8d51bff0acc408504b76521d02030de56a8a3c1e830083e89b89d2 AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# zlib fix the pinned base predates (CVE-2026-4738, reported by Grype; Trivy does not flag it).
# The exact version fails the build once Alpine supersedes it; drop it when the base carries it.
RUN apk add --no-cache zlib=1.4-r0 \
    && addgroup -S -g 10001 florabase \
    && adduser -S -D -H -u 10001 -G florabase -h /app florabase \
    && install --directory --owner=10001 --group=10001 --mode=0700 /var/lib/florabase/attachments

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
RUN /opt/venv/bin/python -m pip uninstall --yes pip \
    && /usr/local/bin/python -m pip uninstall --yes pip
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts/attachment_artifacts.py ./scripts/attachment_artifacts.py

COPY LICENSE /usr/share/licenses/florabase/LICENSE
ARG VERSION=0.1.0-beta.3
ARG REVISION=unknown
ARG SOURCE=https://github.com/alessandrorossato/florabase
LABEL org.opencontainers.image.title="Florabase backend" \
    org.opencontainers.image.version=$VERSION \
    org.opencontainers.image.revision=$REVISION \
    org.opencontainers.image.source=$SOURCE \
    org.opencontainers.image.licenses="AGPL-3.0-or-later"
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=3)"
RUN find /usr /bin /sbin -xdev -type f -perm /6000 -exec chmod a-s {} +
USER florabase
EXPOSE 8000
CMD ["uvicorn", "florabase.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--no-proxy-headers"]

FROM development-builder AS development
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
