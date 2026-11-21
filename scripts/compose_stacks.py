"""Workflow Compose stacks derived from compose.dev.yaml at run time (ADR 0008, WF-09).

The repository tracks two Compose files: the release compose.yaml and the standalone
compose.dev.yaml. Every other workflow stack is compose.dev.yaml plus override files generated
here into untracked state. Each override is written once under a content-addressed name, so
concurrent callers share identical files and a stale file can never be read for a newer text.
Trees from before WF-09 still carry their own overlay files and keep using them.
"""

from __future__ import annotations

import hashlib
import os
import runpy
import stat
import tempfile
from pathlib import Path

DEV = "compose.dev.yaml"

# Override texts. "production" turns the development stack into the source-built production
# targets that the old compose.runtime.yaml described; the others are unchanged from their former
# tracked files.
OVERRIDES: dict[str, str] = {
    "production": """\
name: florabase-prod

services:
  dev-state-init:
    profiles: [development-state]

  db:
    labels: !reset {}
    ports: !reset []

  backend:
    labels: !reset {}
    image: !reset null
    build: !override
      context: ./backend
      target: runtime
    user: !reset null
    environment: !override
      FLORABASE_ENVIRONMENT: production
      FLORABASE_DATABASE_URL: ${FLORABASE_DATABASE_URL:?Set FLORABASE_DATABASE_URL in .env}
      FLORABASE_CANONICAL_ORIGIN: ${FLORABASE_CANONICAL_ORIGIN:-}
      FLORABASE_COOKIE_MODE: secure
      FLORABASE_CORS_ORIGINS: ${FLORABASE_CORS_ORIGINS:-[]}
      FLORABASE_LOG_LEVEL: ${FLORABASE_LOG_LEVEL:-INFO}
      FLORABASE_LOG_FORMAT: ${FLORABASE_LOG_FORMAT:-json}
      FLORABASE_ATTACHMENT_STORAGE_ROOT: /var/lib/florabase/attachments
    volumes: !override
      - attachment_data:/var/lib/florabase/attachments
    depends_on: !override
      db:
        condition: service_healthy
    ports: !reset []

  frontend:
    labels: !reset {}
    image: !reset null
    build: !override
      context: ./frontend
      target: runtime
    user: !reset null
    environment: !reset {}
    depends_on: !override
      backend:
        condition: service_healthy
    volumes: !reset []
    ports: !override
      - "${APP_BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8080}:8080"
    healthcheck: !override
      test:
        [
          "CMD",
          "wget",
          "--quiet",
          "--tries=1",
          "--spider",
          "http://127.0.0.1:8080/healthz",
        ]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 5s

volumes: !override
  postgres_data:
  attachment_data:
""",
    "review": """\
name: florabase-feature-review

x-source: &source
  io.florabase.role: ${FLORABASE_ROLE:-review}
  io.florabase.source: ${FLORABASE_SOURCE:?Source worktree is required}
  io.florabase.branch: ${FLORABASE_BRANCH:?Source branch is required}
  io.florabase.sha: ${FLORABASE_SHA:?Source SHA is required}
  io.florabase.dirty: ${FLORABASE_DIRTY:?Source dirty state is required}

services:
  db:
    ports: !reset []
    labels: *source
  backend:
    ports: !reset []
    labels: *source
  frontend:
    labels: *source

volumes:
  postgres_data:
    labels:
      io.florabase.source: ${FLORABASE_SOURCE}
  attachment_data:
    labels:
      io.florabase.source: ${FLORABASE_SOURCE}
  frontend_node_modules:
    labels:
      io.florabase.source: ${FLORABASE_SOURCE}
""",
    "sourcing": """\
services:
  backend:
    environment:
      FLORABASE_ENVIRONMENT: development
      FLORABASE_CANONICAL_ORIGIN: http://localhost:15175
      FLORABASE_COOKIE_MODE: loopback-development
      FLORABASE_LOG_FORMAT: text
      FLORABASE_CORS_ORIGINS: "[]"

  frontend:
    ports: !override
      - "127.0.0.1:15175:5173"
""",
    "uat": """\
services:
  backend:
    environment:
      FLORABASE_WORKFLOW_MODE: uat
      FLORABASE_UAT_PROJECT: ${COMPOSE_PROJECT_NAME:?UAT project required}
      FLORABASE_UAT_SOURCE: ${FLORABASE_SOURCE:?UAT source required}
      FLORABASE_WCVP_SNAPSHOT_PATH: /app/src/.source-cache/wcvp-v15.sqlite
      FLORABASE_WFO_SNAPSHOT_PATH: /app/src/.source-cache/wfo-2026-06.sqlite
""",
    "uat-instance": """\
x-instance: &instance
  io.florabase.source: ${FLORABASE_SOURCE:?UAT instance source required}
  io.florabase.uat.instance: ${FLORABASE_UAT_INSTANCE:?UAT instance name required}
  io.florabase.uat.port: ${FRONTEND_PORT:?UAT instance port required}
  io.florabase.uat.profile: ${FLORABASE_UAT_PROFILE:?UAT instance dataset profile required}

services:
  backend:
    environment:
      FLORABASE_WORKFLOW_MODE: uat-instance

volumes:
  postgres_data:
    labels: *instance
  attachment_data:
    labels: *instance
  frontend_node_modules:
    labels: *instance
""",
    "quality": """\
x-owner: &owner
  io.florabase.workflow.lifecycle: quality
  io.florabase.workflow.owner: ${FLORABASE_WORKFLOW_OWNER:?Quality metadata required}
  io.florabase.workflow.source: ${FLORABASE_SOURCE:?Quality source required}

services:
  db:
    labels: *owner
    network_mode: none
    networks: !reset []
    ports: !reset []
  backend:
    labels: *owner
    network_mode: none
    networks: !reset []
    ports: !reset []
    build:
      labels:
        <<: *owner
        com.docker.compose.project: ${COMPOSE_PROJECT_NAME:?Quality project required}
  frontend:
    labels: *owner
    network_mode: none
    networks: !reset []
    ports: !reset []
    environment:
      # Keep the full jsdom suite stable on small linked-worktree hosts.
      VITEST_MAX_WORKERS: "1"
      FLORABASE_QUALITY_OFFLINE: "1"
    build:
      labels:
        <<: *owner
        com.docker.compose.project: ${COMPOSE_PROJECT_NAME:?Quality project required}
  dev-state-init:
    labels: *owner
    network_mode: none
    networks: !reset []
    build:
      labels:
        <<: *owner
        com.docker.compose.project: ${COMPOSE_PROJECT_NAME:?Quality project required}
networks: !reset {}
volumes:
  postgres_data:
    labels: *owner
  attachment_data:
    labels: *owner
  frontend_node_modules:
    labels: *owner
""",
    "quality-network": """\
x-owner: &owner
  io.florabase.workflow.lifecycle: quality
  io.florabase.workflow.owner: ${FLORABASE_WORKFLOW_OWNER:?Quality metadata required}
  io.florabase.workflow.source: ${FLORABASE_SOURCE:?Quality source required}

services:
  backend:
    network_mode: bridge
    networks: !reset []
    ports: !reset []
    environment:
      HOME: /tmp/florabase-backend-home
      XDG_CACHE_HOME: /tmp/florabase-backend-cache
  frontend:
    network_mode: bridge
    networks: !reset []
    ports: !reset []
    environment:
      FLORABASE_QUALITY_OFFLINE: "0"
  frontend-lockfile:
    labels: *owner
    image: ${COMPOSE_PROJECT_NAME:?Quality project required}-frontend-toolchain
    build:
      context: ./frontend
      target: toolchain
      labels:
        <<: *owner
        com.docker.compose.project: ${COMPOSE_PROJECT_NAME:?Quality project required}
    user: "${LOCAL_UID:-1000}:${LOCAL_GID:-1000}"
    network_mode: bridge
    networks: !reset []
    ports: !reset []
    environment:
      HOME: /tmp/florabase-frontend-home
      COREPACK_ENABLE_DOWNLOAD_PROMPT: "0"
    volumes:
      - ./frontend:/app
    working_dir: /app
    restart: "no"
""",
    "preview": """\
services:
  db:
    labels:
      io.florabase.preview.ref: ${FLORABASE_PREVIEW_REF:?Preview ref is required}
      io.florabase.preview.sha: ${FLORABASE_PREVIEW_SHA:?Preview SHA is required}

  backend:
    environment:
      FLORABASE_ENVIRONMENT: development
      FLORABASE_CANONICAL_ORIGIN: http://localhost:15173
      FLORABASE_COOKIE_MODE: loopback-development
      FLORABASE_CORS_ORIGINS: "[]"
      FLORABASE_LOG_FORMAT: text
    labels:
      io.florabase.preview.ref: ${FLORABASE_PREVIEW_REF:?Preview ref is required}
      io.florabase.preview.sha: ${FLORABASE_PREVIEW_SHA:?Preview SHA is required}

  frontend:
    ports: !override
      - "127.0.0.1:15173:8080"
    labels:
      io.florabase.preview.ref: ${FLORABASE_PREVIEW_REF:?Preview ref is required}
      io.florabase.preview.sha: ${FLORABASE_PREVIEW_SHA:?Preview SHA is required}
""",
    "perf": """\
services:
  db:
    environment:
      POSTGRES_DB: florabase_perf
      POSTGRES_USER: florabase_perf
      POSTGRES_PASSWORD: disposable-perf-password
    volumes: !reset []
    tmpfs:
      - /var/lib/postgresql
    command: [postgres, -c, shared_preload_libraries=pg_stat_statements]
  backend:
    environment:
      FLORABASE_ENVIRONMENT: development
      FLORABASE_DATABASE_URL: postgresql+psycopg://florabase_perf:disposable-perf-password@db:5432/florabase_perf
      FLORABASE_DATABASE_DISPOSABLE: "true"
      FLORABASE_CANONICAL_ORIGIN: http://localhost:18080
      FLORABASE_COOKIE_MODE: loopback-development
    volumes: !reset []
    tmpfs:
      - /var/lib/florabase/attachments:uid=10001,gid=10001,mode=0700
  frontend:
    ports: !override
      - "127.0.0.1:18080:8080"
""",
    "integration": """\
name: florabase-integration

services:
  db:
    image: postgres:18.6-alpine
    environment:
      POSTGRES_DB: florabase_integration
      POSTGRES_USER: florabase_integration
      POSTGRES_PASSWORD: disposable-integration-password
    tmpfs:
      - /var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 2s
      timeout: 5s
      retries: 15
      start_period: 5s
    networks: [integration]

  tests:
    build:
      context: ./backend
      target: development
    environment:
      FLORABASE_ENVIRONMENT: test
      FLORABASE_DATABASE_URL: postgresql+psycopg://florabase_integration:disposable-integration-password@db:5432/florabase_integration
      FLORABASE_DATABASE_DISPOSABLE: "true"
      FLORABASE_CANONICAL_ORIGIN: http://testserver
      FLORABASE_ATTACHMENT_STORAGE_ROOT: /tmp/florabase-attachments
      COVERAGE_FILE: /tmp/florabase-integration-coverage
      PYTEST_ADDOPTS: -o cache_dir=/tmp/florabase-integration-pytest --durations=20 --durations-min=0.1
    depends_on:
      db:
        condition: service_healthy
    command:
      - /bin/sh
      - -ec
      - |
        python -c 'from florabase.core.config import get_settings; from florabase.db.testing import require_disposable_test_database; require_disposable_test_database(get_settings())'
        alembic upgrade head
        pytest --no-cov -m integration
    networks: [integration]
    init: true
    volumes:
      - ./scripts:/review:ro
    tmpfs:
      - /tmp/florabase-attachments:mode=0700

networks:
  integration:
""",
}

# Each stack lists the overrides applied after compose.dev.yaml, in order.
STACKS: dict[str, tuple[str, ...]] = {
    "dev": (),
    "prod": ("production",),
    "review": ("review",),
    "sourcing": ("review", "sourcing"),
    "uat": ("review", "uat"),
    "uat-instance": ("review", "uat", "uat-instance"),
    "quality": ("quality",),
    "quality-network": ("quality", "quality-network"),
    "preview": ("production", "preview"),
    "perf": ("production", "perf"),
}

# Legacy tree file names for the same stacks; the base is resolved separately.
LEGACY: dict[str, tuple[str, ...]] = {
    "dev": ("compose.dev.yaml",),
    "prod": (),
    "review": ("compose.dev.yaml", "compose.review.yaml"),
    "sourcing": ("compose.dev.yaml", "compose.review.yaml", "compose.sourcing.yaml"),
    "uat": ("compose.dev.yaml", "compose.review.yaml", "compose.uat.yaml"),
    "uat-instance": (
        "compose.dev.yaml",
        "compose.review.yaml",
        "compose.uat.yaml",
        "compose.uat-instance.yaml",
    ),
    "quality": ("compose.dev.yaml", "compose.quality.yaml"),
    "quality-network": ("compose.dev.yaml", "compose.quality.yaml", "compose.quality-network.yaml"),
    "preview": ("compose.preview.yaml",),
    "perf": ("compose.perf.yaml",),
}


def is_legacy(source: Path) -> bool:
    """A tree from before WF-09 has no stack definitions and tracks its own workflow overlays."""
    return not (source / "scripts" / "compose_stacks.py").is_file()


def definitions(source: Path) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    """The override texts and stacks of the tree at source, which pair with its compose.dev.yaml."""
    module = (source / "scripts" / "compose_stacks.py").resolve()
    if module == Path(__file__).resolve():
        return OVERRIDES, STACKS
    # Another tree (a previewed ref, a delivered owner) carries its own definitions.
    loaded = runpy.run_path(str(module))
    return dict(loaded["OVERRIDES"]), dict(loaded["STACKS"])


def state_directory() -> Path:
    """Untracked per-checkout state for generated overrides: this checkout's Git directory."""
    for folder in Path(__file__).resolve().parents:
        marker = folder / ".git"
        if marker.is_dir():
            return marker / "florabase-compose"
        if marker.is_file():
            # A linked worktree: ".git" names its private Git directory.
            text = marker.read_text().strip()
            if text.startswith("gitdir: "):
                return (folder / text.removeprefix("gitdir: ")).resolve() / "florabase-compose"
    # Copied tooling outside a checkout (release smoke artifacts): a private per-user directory.
    fallback = Path(tempfile.gettempdir()) / f"florabase-compose-{os.getuid()}"
    fallback.mkdir(mode=0o700, exist_ok=True)
    status = fallback.lstat()
    if not stat.S_ISDIR(status.st_mode) or status.st_uid != os.getuid() or status.st_mode & 0o077:
        raise RuntimeError(f"{fallback} is not a private directory of this user")
    return fallback


def override(name: str, directory: Path | None = None, text: str | None = None) -> Path:
    """Write one override under a content-addressed name and return its path."""
    text = OVERRIDES[name] if text is None else text
    directory = directory or state_directory()
    # The former tracked file name keeps logs, Compose labels and tooling matches readable.
    folder = directory / hashlib.sha256(text.encode()).hexdigest()[:16]
    path = folder / f"compose.{name}.yaml"
    if path.is_file() and path.read_text() == text:
        return path
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=folder, prefix=f".compose.{name}-", suffix=".yaml", delete=False
    ) as temporary:
        temporary.write(text)
    os.replace(temporary.name, path)
    return path


def files(source: Path, stack: str, directory: Path | None = None) -> list[Path]:
    """Compose files for a stack of the tree at source, in load order."""
    if is_legacy(source):
        renamed = source / "compose.runtime.yaml"
        base = renamed if renamed.is_file() else source / "compose.yaml"
        return [base, *(source / name for name in LEGACY[stack])]
    overrides, stacks = definitions(source)
    return [
        source / DEV,
        *(override(name, directory, overrides[name]) for name in stacks[stack]),
    ]


def integration(source: Path | None = None, directory: Path | None = None) -> Path:
    """The standalone disposable integration stack of the tree at source (default: this one)."""
    overrides = definitions(source)[0] if source is not None else OVERRIDES
    return override("integration", directory, overrides["integration"])


def main() -> None:
    """Print one Compose file per line for a stack: compose_stacks.py <source> <stack>."""
    import sys

    source, stack = Path(sys.argv[1]), sys.argv[2]
    paths = [integration()] if stack == "integration" else files(source, stack)
    print("\n".join(str(path) for path in paths))


if __name__ == "__main__":
    main()
