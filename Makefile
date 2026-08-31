SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose
DEV_COMPOSE := $(COMPOSE) -f compose.yaml -f compose.dev.yaml
BACKUP_DIR ?= backups

.PHONY: help setup up dev down logs build test test-backend test-integration test-frontend lint format format-check typecheck check migrate migration backup restore health api-generate api-check dependency-update

help:
	@awk 'BEGIN {FS = ":.*## "; print "Florabase commands:"} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create local environment configuration
	@test ! -e .env || { echo ".env already exists; leaving it unchanged"; exit 0; }
	cp .env.example .env

up: ## Build and start the production-oriented stack
	$(COMPOSE) up --detach --build

dev: ## Start the hot-reloading development stack
	$(DEV_COMPOSE) up --build

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

migrate: ## Apply all pending database migrations explicitly
	$(COMPOSE) run --rm backend alembic upgrade head

migration: ## Create a migration: make migration MESSAGE="describe change"
	@test -n "$(MESSAGE)" || { echo 'MESSAGE is required'; exit 2; }
	$(DEV_COMPOSE) run --rm backend alembic revision --autogenerate -m "$(MESSAGE)"

backup: ## Create a timestamped custom-format PostgreSQL dump
	BACKUP_DIR="$(BACKUP_DIR)" ./scripts/backup.sh

restore: ## Restore dump: make restore FILE=backups/file.dump CONFIRM_REPLACE=yes CONFIRM_DATABASE=name
	@test -n "$(FILE)" || { echo 'FILE is required'; exit 2; }
	FILE="$(FILE)" CONFIRM_REPLACE="$(CONFIRM_REPLACE)" CONFIRM_DATABASE="$(CONFIRM_DATABASE)" ./scripts/restore.sh

health: ## Verify frontend, liveness, and database readiness through the proxy
	./scripts/health.sh

dependency-update: ## Refresh lockfiles after reviewing direct pins
	$(DEV_COMPOSE) run --rm --no-deps backend pip-compile --strip-extras --output-file requirements.lock pyproject.toml
	$(DEV_COMPOSE) run --rm --no-deps backend pip-compile --strip-extras --extra dev --output-file requirements-dev.lock pyproject.toml
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm install --lockfile-only
