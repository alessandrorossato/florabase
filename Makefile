SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := python3 ./scripts/workflow_environment.py prod compose --
DEV_COMPOSE := python3 ./scripts/workflow_environment.py quality compose --
BACKUP_DIR ?= backups
REF ?= origin/main
PREVIEW_PATH ?=
LOGIN ?= owner

.PHONY: uat-preview-remove uat-preview-up uat-preview-status uat-preview-seed uat-preview-stop uat-preview-reset test-uat-preview smoke-uat-preview smoke-dev-upgrade smoke-dev-recovery dev-bootstrap-owner workflow-check feature-init dev-up dev-status dev-stop feature-review-up feature-review-status feature-review-stop feature-review-remove feature-review-bootstrap-owner test-environment-workflow smoke-environment-workflow help setup up dev down logs build test test-backend test-integration test-frontend lint format format-check typecheck check ci migrate dev-upgrade migration backup restore health api-generate api-check dependency-update preview preview-status preview-stop preview-bootstrap-owner preview-import-dev preview-remove feature-start feature-worktree feature-attach feature-context feature-claim feature-handoff feature-retire feature-verify feature-deliver feature-finish test-workflow-helpers test-agent-workflow test-feature-workflow test-preview-workflow

help:
	@awk 'BEGIN {FS = ":.*## "; print "Florabase commands:"} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create local environment configuration
	@if [ -e .env ] || [ -L .env ]; then \
		echo ".env already exists; leaving it unchanged"; \
	else \
		cp -n .env.example .env; \
	fi

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

.PHONY: golden-dataset-check
golden-dataset-check: ## Generate and validate isolated SMOKE golden copies in a disposable Compose project
	./scripts/test-integration.sh backend/tests/integration/test_golden_dataset.py

.PHONY: golden-dataset-comprehensive-check
golden-dataset-comprehensive-check: ## Generate, verify and damage COMPREHENSIVE golden copies in a disposable Compose project; manual
	./scripts/test-integration.sh backend/tests/integration/test_golden_comprehensive.py

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

check: format-check lint typecheck api-check test ## Run the main non-destructive verification suite (cheap static checks first)

ci: test-verification-impact test-workflow-resources test-workflow-helpers test-agent-workflow test-feature-workflow test-preview-workflow test-environment-workflow test-uat-preview workflow-check check test-integration build ## Run the complete local equivalent of pull-request CI

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
	$(DEV_COMPOSE) run --rm --no-deps backend pip-compile --generate-hashes --strip-extras --output-file requirements.lock pyproject.toml
	$(DEV_COMPOSE) run --rm --no-deps backend pip-compile --strip-extras --extra dev --output-file requirements-dev.lock pyproject.toml
	$(DEV_COMPOSE) run --rm --no-deps frontend pnpm install --lockfile-only

feature-init: export BRANCH := $(BRANCH)
feature-init: ## Validate/attach feature context in an existing agent-provided or manual worktree
	@python3 ./scripts/workflow_environment.py init

feature-start: export BRANCH := $(BRANCH)
feature-start: ## Create a branch from updated main: make feature-start BRANCH=feat/example
	@./scripts/feature-start.sh

feature-worktree: export BRANCH := $(BRANCH)
feature-worktree: ## Create a sibling worktree from fetched main: make feature-worktree BRANCH=feat/example
	@python3 ./scripts/feature_worktree.py create

feature-attach: export BRANCH := $(BRANCH)
feature-attach: ## Locate and validate an existing feature worktree without changing it
	@python3 ./scripts/feature_worktree.py attach

feature-context: export BRANCH := $(BRANCH)
feature-context: ## Report branch/SHA/base/writer/receipt/resources; FORMAT=json for machine output
	@python3 ./scripts/feature_worktree.py context $(if $(filter json,$(FORMAT)),--json)

feature-claim: ## Become the one writer, validating any handoff: make feature-claim AGENT_ID=codex
	@python3 ./scripts/feature_worktree.py claim

feature-handoff: ## Release to the next writer: make feature-handoff AGENT_ID=codex TO=opencode REPORT=/outside/report.json
	@python3 ./scripts/feature_worktree.py handoff

feature-retire: ## Remove one finished managed worktree: make feature-retire FEATURE=id CONFIRM_RETIRE=id
	@python3 ./scripts/feature_worktree.py retire

feature-verify: ## Derive affected/full verification automatically and write the exact receipt
	@./scripts/feature-verify.sh

verify-affected: feature-verify ## Alias for the automatic safe final gate (may escalate FULL)

verify-full: ## Force the complete final local gate and exact receipt
	@./scripts/feature-verify.sh --full

verification-plan: ## Show the deterministic impact plan; FORMAT=json for machine output
	@python3 ./scripts/verification_impact.py --base "$(REF)" $(if $(filter json,$(FORMAT)),--json,)

verify-build: ## Build selected independent production images in a disposable owned project
	@python3 ./scripts/disposable_workflow.py verification-build $(foreach service,$(SERVICES),--build $(service))

quality-status: ## Inspect exactly this worktree's reusable Quality project
	@python3 ./scripts/workflow_resources.py quality-status

quality-clean: ## Retire exactly this worktree's Quality resources, preserving other environments
	@python3 ./scripts/workflow_resources.py quality-clean

workflow-resources: ## Report Florabase workflow resource identities and retained cache policy
	@python3 ./scripts/workflow_resources.py report

test-verification-impact: ## Test complete-tree impact selection and selected receipt evidence offline
	@python3 ./scripts/test-verification-impact.py

test-workflow-resources: ## Test exact ownership, failure cleanup and lifecycle safety offline
	@python3 ./scripts/test-workflow-resources.py

smoke-migration-cycle: ## Probe FULL migration execution/failure and PostgreSQL cleanup on disposable fixtures
	@python3 ./scripts/smoke-migration-cycle.py

smoke-workflow-resources: ## Prove retirement and protected-project isolation on unique synthetic Docker state
	@python3 ./scripts/smoke-workflow-resources.py

feature-deliver: ## Push the verified committed feature and wait for protected squash auto-merge
	@./scripts/feature-deliver.py

feature-finish: ## Remove the current local branch after its GitHub PR was merged
	@./scripts/feature-finish.sh

test-workflow-helpers: ## Test Git and database-upgrade helper safety in isolated fixtures
	@./scripts/test-workflow-helpers.sh

test-agent-workflow: ## Test provider-neutral worktree, writer, handoff, lock and retirement safety offline
	@python3 ./scripts/test-agent-workflow.py

test-feature-workflow: ## Test feature verification and delivery orchestration without GitHub
	@python3 ./scripts/test-feature-workflow.py

test-preview-workflow: ## Test stable-preview safety and isolation without Docker or network
	@python3 ./scripts/test-preview-workflow.py

feature-review-up: ## Build dirty current worktree, migrate isolated Review DB, wait for health
	@python3 ./scripts/workflow_environment.py review up

feature-review-status: ## Identify exactly which source and database Feature Review uses
	@python3 ./scripts/workflow_environment.py review status

.PHONY: feature-review-seed
feature-review-seed: ## Seed representative synthetic data in exactly owned Review; retain owner/edits
	@python3 ./scripts/workflow_environment.py review seed

.PHONY: feature-review-extended-seed feature-review-extended-status
feature-review-extended-seed: ## Add Review-only Botanical Dataset v5; preserve v4, owner and edits
	@python3 ./scripts/workflow_environment.py review extended-seed

feature-review-extended-status: ## Inspect guarded Review v5 references and category counts
	@python3 ./scripts/workflow_environment.py review extended-status

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

workflow-check: test-dependabot-policy test-beta-images test-beta-runtime ## Lint, format-check and strictly type-check the new environment helpers
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" backend ruff check --no-cache --isolated --select E4,E7,E9,F,I,B,UP /workflow/workflow_resources.py /workflow/feature_worktree.py /workflow/test-agent-workflow.py /workflow/smoke_lifecycle.py /workflow/disposable_workflow.py /workflow/verification_impact.py /workflow/verification_gate.py /workflow/ci-verify.py /workflow/feature-tree-fingerprint.py /workflow/test-verification-impact.py /workflow/test-workflow-resources.py /workflow/smoke-workflow-resources.py /workflow/smoke-migration-cycle.py /workflow/workflow_environment.py /workflow/sourcing_preview.py /workflow/test-environment-workflow.py /workflow/smoke-environment-workflow.py /workflow/smoke-dev-recovery.py /workflow/smoke-dev-upgrade.py /workflow/uat_source.py /workflow/uat_preview.py /workflow/uat_instance.py /workflow/test-uat-instance.py /workflow/smoke-uat-instance.py /workflow/test-uat-source.py /workflow/test-uat-preview.py /workflow/smoke-uat-preview.py /workflow/uat_fixture.py /workflow/review_dataset_v5.py /workflow/golden_plan.py /workflow/golden_dataset.py /workflow/test-uat-fixture.py /workflow/test-review-fixture.py /workflow/beta_release.py /workflow/beta-release-checks.py /workflow/publish-beta-images.py /workflow/smoke-beta-images.py /workflow/rehearse-beta-release.py /workflow/build-beta-candidate.py /workflow/test-beta-images.py /workflow/test-release-tools-lock.py /workflow/release-tools.py /workflow/test-beta-lifecycle.py /workflow/smoke-beta-runtime.py /workflow/smoke-portable-compose.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" backend ruff format --no-cache --check /workflow/workflow_resources.py /workflow/feature_worktree.py /workflow/test-agent-workflow.py /workflow/smoke_lifecycle.py /workflow/disposable_workflow.py /workflow/verification_impact.py /workflow/verification_gate.py /workflow/ci-verify.py /workflow/feature-tree-fingerprint.py /workflow/test-verification-impact.py /workflow/test-workflow-resources.py /workflow/smoke-workflow-resources.py /workflow/smoke-migration-cycle.py /workflow/workflow_environment.py /workflow/sourcing_preview.py /workflow/test-environment-workflow.py /workflow/smoke-environment-workflow.py /workflow/smoke-dev-recovery.py /workflow/smoke-dev-upgrade.py /workflow/uat_source.py /workflow/uat_preview.py /workflow/uat_instance.py /workflow/test-uat-instance.py /workflow/smoke-uat-instance.py /workflow/test-uat-source.py /workflow/test-uat-preview.py /workflow/smoke-uat-preview.py /workflow/uat_fixture.py /workflow/review_dataset_v5.py /workflow/golden_plan.py /workflow/golden_dataset.py /workflow/test-uat-fixture.py /workflow/test-review-fixture.py /workflow/beta_release.py /workflow/beta-release-checks.py /workflow/publish-beta-images.py /workflow/smoke-beta-images.py /workflow/rehearse-beta-release.py /workflow/build-beta-candidate.py /workflow/test-beta-images.py /workflow/test-release-tools-lock.py /workflow/release-tools.py /workflow/test-beta-lifecycle.py /workflow/smoke-beta-runtime.py /workflow/smoke-portable-compose.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" backend mypy --strict --follow-imports=skip /workflow/workflow_resources.py /workflow/feature_worktree.py /workflow/test-agent-workflow.py /workflow/smoke_lifecycle.py /workflow/disposable_workflow.py /workflow/verification_impact.py /workflow/verification_gate.py /workflow/ci-verify.py /workflow/feature-tree-fingerprint.py /workflow/smoke-workflow-resources.py /workflow/smoke-migration-cycle.py /workflow/workflow_environment.py /workflow/sourcing_preview.py /workflow/smoke-environment-workflow.py /workflow/smoke-dev-recovery.py /workflow/smoke-dev-upgrade.py /workflow/uat_source.py /workflow/uat_preview.py /workflow/uat_instance.py /workflow/smoke-uat-instance.py /workflow/smoke-uat-preview.py /workflow/beta_release.py /workflow/beta-release-checks.py /workflow/publish-beta-images.py /workflow/smoke-beta-images.py /workflow/rehearse-beta-release.py /workflow/build-beta-candidate.py /workflow/test-beta-images.py /workflow/test-release-tools-lock.py /workflow/release-tools.py /workflow/test-beta-lifecycle.py /workflow/smoke-beta-runtime.py /workflow/smoke-portable-compose.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR):/repo:ro" backend ruff check --no-cache --isolated --target-version py38 --select E4,E7,E9,F,I,B,UP /repo/deploy/beta/florabasectl.py /repo/scripts/smoke_beta_runtime_client.py /repo/scripts/test-beta-runtime.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR):/repo:ro" backend ruff format --no-cache --isolated --line-length 100 --target-version py38 --check /repo/deploy/beta/florabasectl.py /repo/scripts/smoke_beta_runtime_client.py /repo/scripts/test-beta-runtime.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR):/repo:ro" backend mypy --strict /repo/deploy/beta/florabasectl.py /repo/scripts/smoke_beta_runtime_client.py /repo/scripts/test-beta-runtime.py
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR)/scripts:/workflow:ro" -e MYPYPATH=/app/src:/workflow backend mypy --strict --follow-imports=skip /workflow/uat_fixture.py /workflow/review_dataset_v5.py /workflow/golden_plan.py /workflow/golden_dataset.py /app/scripts/verify_migration_cycle.py


UAT_HELPER := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts/uat_preview.py

uat-preview-up: ## Start/rebuild owned UAT from feature or delivered detached source; preserve data
	@python3 "$(UAT_HELPER)" up

uat-preview-status: ## Show UAT Preview source, health, migrations and fixture state
	@python3 "$(UAT_HELPER)" status

uat-preview-seed: ## Explicitly create standard UAT-only owner and synthetic baseline
	@python3 "$(UAT_HELPER)" seed

uat-preview-sync: ## Explicitly advance the clean delivered owner to fetched origin/main, preserving all volumes
	@python3 "$(UAT_HELPER)" sync

uat-preview-stop: ## Stop UAT Preview, preserving database/media/dependencies
	@python3 "$(UAT_HELPER)" stop

UAT_RETIREMENT_HELPER := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts/uat_preview.py
uat-preview-remove: export CONFIRM_REMOVE_UAT_PREVIEW := $(CONFIRM_REMOVE_UAT_PREVIEW)
uat-preview-remove: ## Retire ONLY owning UAT state; CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview
	@python3 "$(UAT_RETIREMENT_HELPER)" remove

UAT_INSTANCE_HELPER := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts/uat_instance.py
PROFILE ?=

.PHONY: uat-instance-up uat-instance-status uat-instance-seed uat-instance-validate uat-instance-stop uat-instance-reset uat-instance-remove uat-instance-list smoke-uat-instance
uat-instance-up: ## Start/rebuild THIS worktree's own UAT instance (port 15180-15183); PROFILE=smoke|comprehensive on first use
	@python3 "$(UAT_INSTANCE_HELPER)" up --profile "$(PROFILE)"

uat-instance-status: ## Show this worktree's instance: project, port, source/SHA, migrations, dataset manifest
	@python3 "$(UAT_INSTANCE_HELPER)" status

uat-instance-seed: ## Explicitly generate the instance's golden SMOKE/COMPREHENSIVE dataset (idempotent)
	@python3 "$(UAT_INSTANCE_HELPER)" seed --profile "$(PROFILE)"

uat-instance-validate: ## Verify the instance dataset against the reviewed golden baseline (exit 0/1/3/4)
	@python3 "$(UAT_INSTANCE_HELPER)" validate

uat-instance-stop: ## Stop this worktree's instance, preserving its DB/media/dependencies
	@python3 "$(UAT_INSTANCE_HELPER)" stop

uat-instance-reset: export CONFIRM_RESET_UAT_INSTANCE := $(CONFIRM_RESET_UAT_INSTANCE)
uat-instance-reset: ## Recreate ONLY this instance and reseed; CONFIRM_RESET_UAT_INSTANCE=<its project> [PROFILE=...]
	@python3 "$(UAT_INSTANCE_HELPER)" reset --profile "$(PROFILE)"

uat-instance-remove: export CONFIRM_REMOVE_UAT_INSTANCE := $(CONFIRM_REMOVE_UAT_INSTANCE)
uat-instance-remove: ## Retire ONLY this instance's containers/network/volumes/image tags; CONFIRM_REMOVE_UAT_INSTANCE=<its project>
	@python3 "$(UAT_INSTANCE_HELPER)" remove

uat-instance-list: ## Read-only machine-wide list of UAT instance slots, owners and state
	@python3 "$(UAT_INSTANCE_HELPER)" list

smoke-uat-instance: ## Prove two coexisting instances, isolation, refusals and exact cleanup on disposable state
	@python3 ./scripts/smoke-uat-instance.py

SOURCING_HELPER := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))scripts/sourcing_preview.py

sourcing-preview-up: ## Build current worktree, migrate isolated Sourcing DB, wait for health
	@python3 "$(SOURCING_HELPER)" up

sourcing-preview-status: ## Show Sourcing Preview source, health, migrations and dataset coverage
	@python3 "$(SOURCING_HELPER)" status

sourcing-preview-seed: ## Seed synthetic Suppliers/Orders/SeedLots in exactly owned Sourcing Preview
	@python3 "$(SOURCING_HELPER)" seed

sourcing-preview-bootstrap-owner: ## Create the Sourcing owner: make sourcing-preview-bootstrap-owner LOGIN=owner
	@python3 "$(SOURCING_HELPER)" bootstrap-owner --login "$(LOGIN)"

sourcing-preview-stop: ## Stop Sourcing Preview, preserving database/media/dependencies
	@python3 "$(SOURCING_HELPER)" stop

sourcing-preview-remove: export CONFIRM_REMOVE_SOURCING := $(CONFIRM_REMOVE_SOURCING)
sourcing-preview-remove: ## Retire ONLY Sourcing Preview state; CONFIRM_REMOVE_SOURCING=florabase-sourcing-preview
	@python3 "$(SOURCING_HELPER)" remove --confirm "$(CONFIRM_REMOVE_SOURCING)"

sourcing-preview-compose: ## Read-only Sourcing Compose passthrough: make sourcing-preview-compose CMD="ps"
	@python3 "$(SOURCING_HELPER)" compose --cmd "$(CMD)"

uat-preview-reset: export CONFIRM_RESET_UAT_PREVIEW := $(CONFIRM_RESET_UAT_PREVIEW)
uat-preview-reset: ## Recreate ONLY UAT state; CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview
	@python3 "$(UAT_HELPER)" reset

test-dependabot-policy: ## Validate YAML and dependency deferral/group contracts
	$(DEV_COMPOSE) run --rm --no-deps -v "$(CURDIR):/repository:ro" frontend node /repository/scripts/test-dependabot-policy.mjs /repository

test-uat-preview: ## Test UAT workflow identity, retirement, reset and fixture isolation
	@python3 ./scripts/test-uat-preview.py
	@python3 ./scripts/test-uat-source.py
	@python3 ./scripts/test-uat-instance.py

smoke-uat-preview: ## Prove UAT seed/auth/reset/persistence/ownership transition on disposable Compose state
	@python3 ./scripts/smoke-uat-preview.py

.PHONY: verify-affected verify-full verification-plan verify-build quality-status quality-clean workflow-resources test-verification-impact test-workflow-resources smoke-workflow-resources smoke-migration-cycle

.PHONY: sourcing-preview-up sourcing-preview-status sourcing-preview-seed sourcing-preview-bootstrap-owner sourcing-preview-stop sourcing-preview-remove sourcing-preview-compose

.PHONY: uat-preview-sync test-dependabot-policy

.PHONY: ui-lab ui-page
ui-lab: ## Open the development-only UI laboratory on loopback (no API/database required)
	cd frontend && node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 15284 --strictPort

ui-page: export FLORABASE_UI_PAGE_NAME = $(NAME)
ui-page: export FLORABASE_UI_PAGE_ARCHETYPE = $(ARCHETYPE)
ui-page: ## Scaffold an approved composition: NAME=Example ARCHETYPE=directory|activity
	@python3 scripts/ui_page.py

.PHONY: test-beta-images smoke-beta-images test-beta-runtime smoke-beta-runtime
test-beta-images: ## Validate beta release identities and fail-closed publication prerequisites
	@python3 ./scripts/release-tools.py ./scripts/test-beta-images.py
	@python3 ./scripts/test-release-tools-lock.py

smoke-beta-images: ## Build and test disposable local production images (no publication)
	@python3 ./scripts/release-tools.py ./scripts/build-beta-candidate.py --evidence /tmp/florabase-beta-candidate.json

# DSM 7.2 ships Python 3.8; the stdlib-only controller must keep running there.
BETA_RUNTIME_PYTHON := python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f

test-beta-runtime: ## Offline beta stack contract and controller safety rules (host Python and Python 3.8)
	@python3 ./scripts/test-beta-runtime.py -q
	@docker run --rm --network none --read-only --tmpfs /tmp -v "$(CURDIR):/src:ro" -w /src $(BETA_RUNTIME_PYTHON) python -I scripts/test-beta-runtime.py -q --controller-only

smoke-beta-runtime: ## Disposable Engine 24.0.2/Compose 2.20.1 install, recovery and upgrade drills (no real host)
	@python3 ./scripts/smoke-beta-runtime.py --evidence /tmp/florabase-beta-runtime-smoke.json

.PHONY: release-preflight-local
release-preflight-local: ## Rehearse protected release preparation and promotion in an owned local registry
	@set -eo pipefail; \
	run_dir=$$(mktemp -d "$${TMPDIR:-/tmp}/florabase-release-preflight.XXXXXXXX"); \
	echo "Release preflight evidence: $$run_dir"; \
	python3 scripts/release-tools.py scripts/rehearse-beta-release.py --output "$$run_dir/output" 2>&1 | tee "$$run_dir/preflight.log"
