SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := python3 ./scripts/workflow_environment.py prod compose --
DEV_COMPOSE := python3 ./scripts/workflow_environment.py quality compose --
BACKUP_DIR ?= backups
REF ?= origin/main
PREVIEW_PATH ?=
LOGIN ?= owner

.PHONY: uat-preview-remove uat-preview-up uat-preview-status uat-preview-seed uat-preview-stop uat-preview-reset test-uat-preview smoke-uat-preview smoke-dev-upgrade smoke-dev-recovery dev-bootstrap-owner workflow-check feature-init dev-up dev-status dev-stop feature-review-up feature-review-status feature-review-stop feature-review-remove feature-review-bootstrap-owner test-environment-workflow smoke-environment-workflow help setup up dev down logs build test test-backend test-integration test-frontend lint format format-check typecheck check ci migrate dev-upgrade migration backup restore health api-generate api-check dependency-update preview preview-status preview-stop preview-bootstrap-owner preview-import-dev preview-remove feature-start feature-verify feature-deliver feature-finish test-workflow-helpers test-feature-workflow test-preview-workflow

help:
	@awk 'BEGIN {FS = ":.*## "; print "Florabase commands:"} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create local environment configuration
	@test ! -e .env || { echo ".env already exists; leaving it unchanged"; exit 0; }
	cp .env.example .env

up: ## Build and start the production-oriented stack
	$(COMPOSE) up --detach --build

dev: dev-up ## Start the persistent development stack from the primary checkout

dev-up: ## Build/start DEV from the primary checkout, preserving its data
	@python3 ./scripts/workflow_environment.py dev up

dev-status: ## Identify DEV source, project, health and migration state
	@python3 ./scripts/workflow_environment.py dev status

dev-stop: ## Stop identified DEV (including old-source DEV), preserving all state
	@python3 ./scripts/workflow_environment.py dev stop

dev-bootstrap-owner: ## Create DEV owner interactively using the primary checkout
	@python3 ./scripts/workflow_environment.py dev compose -- run --rm backend python -m florabase.auth.bootstrap "$(LOGIN)"

down: ## Stop containers without deleting persistent volumes
	$(COMPOSE) down

logs: ## Follow service logs
	$(COMPOSE) logs --follow

build: ## Build production container images
	$(COMPOSE) build

test: test-backend test-frontend ## Run backend and frontend tests

test-backend:
	$(DEV_COMPOSE) run --rm --no-deps backend pytest -m "not integration"

test-integration: ## Run PostgreSQL-backed integration tests in a disposable Compose project
	./scripts/test-integration.sh

test-frontend:
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm test

lint: ## Run backend and frontend linters
	$(DEV_COMPOSE) run --rm --no-deps backend ruff check .
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm lint

format: ## Format backend and frontend sources
	$(DEV_COMPOSE) run --rm --no-deps backend ruff format .
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm format

format-check: ## Verify formatting without changing files
	$(DEV_COMPOSE) run --rm --no-deps backend ruff format --check .
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm format:check

typecheck: ## Run Python and TypeScript static checks
	$(DEV_COMPOSE) run --rm --no-deps backend mypy
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm typecheck

api-generate: ## Regenerate OpenAPI and TypeScript API declarations
	$(DEV_COMPOSE) run --rm --no-deps backend python scripts/export_openapi.py
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm api:generate

api-check: ## Verify generated API artifacts are current
	./scripts/check-api-generated.sh

check: format-check lint typecheck test api-check ## Run the main non-destructive verification suite

ci: test-workflow-helpers test-feature-workflow test-preview-workflow test-environment-workflow test-uat-preview workflow-check check test-integration build ## Run the complete local equivalent of pull-request CI

migrate: ## Apply all pending database migrations explicitly
	$(COMPOSE) run --rm backend alembic upgrade head

dev-upgrade: ## Upgrade only DEV using its primary checkout migration code
	@python3 ./scripts/workflow_environment.py dev upgrade

migration: ## Create a migration: make migration MESSAGE="describe change"
	@test -n "$(MESSAGE)" || { echo 'MESSAGE is required'; exit 2; }
	python3 ./scripts/workflow_environment.py review compose -- run --rm backend alembic revision --autogenerate -m "$(MESSAGE)"

backup: ## Create coordinated PostgreSQL and attachment-volume backup artifacts
	BACKUP_DIR="$(BACKUP_DIR)" ./scripts/backup.sh

restore: ## Restore database and attachments; see docs/backup-restore.md
	@test -n "$(FILE)" || { echo 'FILE is required'; exit 2; }
	@test -n "$(ATTACHMENTS_FILE)" || { echo 'ATTACHMENTS_FILE is required'; exit 2; }
	FILE="$(FILE)" ATTACHMENTS_FILE="$(ATTACHMENTS_FILE)" CONFIRM_REPLACE="$(CONFIRM_REPLACE)" CONFIRM_DATABASE="$(CONFIRM_DATABASE)" ./scripts/restore.sh

health: ## Verify frontend, liveness, and database readiness through the proxy
	./scripts/health.sh

preview: ## Start/update isolated stable preview: make preview REF=origin/main
	@python3 ./scripts/preview.py --path "$(PREVIEW_PATH)" start --ref "$(REF)"

preview-status: ## Show isolated preview Git, Compose, database, and URL state
	@python3 ./scripts/preview.py --path "$(PREVIEW_PATH)" status

preview-stop: ## Stop preview containers while preserving its worktree and database
	@python3 ./scripts/preview.py --path "$(PREVIEW_PATH)" stop

preview-bootstrap-owner: ## Interactively create the preview owner: make preview-bootstrap-owner LOGIN=owner
	@python3 ./scripts/preview.py --path "$(PREVIEW_PATH)" bootstrap-owner --login "$(LOGIN)"

preview-import-dev: ## Explain the blocked legacy DB-only import (coordinated media clone deferred)
	@python3 ./scripts/preview.py --path "$(PREVIEW_PATH)" import-dev --confirm "$(CONFIRM_REPLACE_PREVIEW)" --confirm-database "$(CONFIRM_DATABASE)"

preview-remove: ## Stop preview and safely remove its clean worktree, preserving its database
	@python3 ./scripts/preview.py --path "$(PREVIEW_PATH)" remove

dependency-update: ## Refresh lockfiles after reviewing direct pins
	$(DEV_COMPOSE) run --rm --no-deps backend pip-compile --strip-extras --output-file requirements.lock pyproject.toml
	$(DEV_COMPOSE) run --rm --no-deps backend pip-compile --strip-extras --extra dev --output-file requirements-dev.lock pyproject.toml
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm install --lockfile-only

feature-init: export BRANCH := $(BRANCH)
feature-init: ## Validate/attach feature context in an existing Codex worktree
	@python3 ./scripts/workflow_environment.py init

feature-start: export BRANCH := $(BRANCH)
feature-start: ## Create a branch from updated main: make feature-start BRANCH=feat/example
	@./scripts/feature-start.sh

feature-verify: ## Run the canonical final local verification gate for the current feature branch
	@./scripts/feature-verify.sh

feature-deliver: ## Push the verified committed feature and wait for protected squash auto-merge
	@./scripts/feature-deliver.py

feature-finish: ## Remove the current local branch after its GitHub PR was merged
	@./scripts/feature-finish.sh

test-workflow-helpers: ## Test Git and database-upgrade helper safety in isolated fixtures
	@./scripts/test-workflow-helpers.sh

test-feature-workflow: ## Test feature verification and delivery orchestration without GitHub
	@python3 ./scripts/test-feature-workflow.py

test-preview-workflow: ## Test stable-preview safety and isolation without Docker or network
	@python3 ./scripts/test-preview-workflow.py

feature-review-up: ## Build dirty current worktree, migrate isolated Review DB, wait for health
	@python3 ./scripts/workflow_environment.py review up

feature-review-status: ## Identify exactly which source and database Feature Review uses
	@python3 ./scripts/workflow_environment.py review status

feature-review-stop: ## Stop Feature Review; preserve all its state
	@python3 ./scripts/workflow_environment.py review stop

feature-review-remove: export CONFIRM_REMOVE_REVIEW := $(CONFIRM_REMOVE_REVIEW)
feature-review-remove: ## Delete ONLY Review resources; CONFIRM_REMOVE_REVIEW=florabase-feature-review
	@python3 ./scripts/workflow_environment.py review remove

feature-review-bootstrap-owner: ## Create isolated Review owner interactively
	@python3 ./scripts/workflow_environment.py review compose -- run --rm backend python -m florabase.auth.bootstrap "$(LOGIN)"

test-environment-workflow: ## Test source/config/migration/resource isolation in local fixtures
	@python3 ./scripts/test-environment-workflow.py

smoke-environment-workflow: ## Run isolated real Compose smoke (never changes operator DEV)
	@python3 ./scripts/smoke-environment-workflow.py

smoke-dev-recovery: ## Prove recovery on unique fixtures without touching operator environments
	@python3 ./scripts/smoke-dev-recovery.py

smoke-dev-upgrade: ## Prove upgrade image freshness/retry on unique disposable state
	@python3 ./scripts/smoke-dev-upgrade.py

workflow-check: ## Lint, format-check and strictly type-check the new environment helpers
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" backend ruff check --no-cache --isolated --select E4,E7,E9,F,I,B,UP /workflow/workflow_environment.py /workflow/test-environment-workflow.py /workflow/smoke-environment-workflow.py /workflow/smoke-dev-recovery.py /workflow/smoke-dev-upgrade.py /workflow/uat_preview.py /workflow/test-uat-preview.py /workflow/smoke-uat-preview.py /workflow/uat_fixture.py /workflow/test-uat-fixture.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" backend ruff format --no-cache --check /workflow/workflow_environment.py /workflow/test-environment-workflow.py /workflow/smoke-environment-workflow.py /workflow/smoke-dev-recovery.py /workflow/smoke-dev-upgrade.py /workflow/uat_preview.py /workflow/test-uat-preview.py /workflow/smoke-uat-preview.py /workflow/uat_fixture.py /workflow/test-uat-fixture.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" backend mypy --strict --follow-imports=skip /workflow/workflow_environment.py /workflow/smoke-environment-workflow.py /workflow/smoke-dev-recovery.py /workflow/smoke-dev-upgrade.py /workflow/uat_preview.py /workflow/smoke-uat-preview.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" -e MYPYPATH=/app/src:/workflow backend mypy --strict --follow-imports=skip /workflow/uat_fixture.py


uat-preview-up: ## Start/rebuild UAT Preview from this feature worktree; preserve data
	@python3 ./scripts/uat_preview.py up

uat-preview-status: ## Show UAT Preview source, health, migrations and fixture state
	@python3 ./scripts/uat_preview.py status

uat-preview-seed: ## Explicitly create standard UAT-only owner and synthetic baseline
	@python3 ./scripts/uat_preview.py seed

uat-preview-stop: ## Stop UAT Preview, preserving database/media/dependencies
	@python3 ./scripts/uat_preview.py stop

UAT_RETIREMENT_HELPER := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts/uat_preview.py
uat-preview-remove: export CONFIRM_REMOVE_UAT_PREVIEW := $(CONFIRM_REMOVE_UAT_PREVIEW)
uat-preview-remove: ## Retire ONLY owning UAT state; CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview
	@python3 "$(UAT_RETIREMENT_HELPER)" remove

uat-preview-reset: export CONFIRM_RESET_UAT_PREVIEW := $(CONFIRM_RESET_UAT_PREVIEW)
uat-preview-reset: ## Recreate ONLY UAT state; CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview
	@python3 ./scripts/uat_preview.py reset

test-uat-preview: ## Test UAT workflow identity, retirement, reset and fixture isolation
	@python3 ./scripts/test-uat-preview.py

smoke-uat-preview: ## Prove UAT seed/auth/reset/persistence/ownership transition on disposable Compose state
	@python3 ./scripts/smoke-uat-preview.py
