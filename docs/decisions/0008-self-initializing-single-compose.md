# ADR 0008: Self-initializing single Compose installation

- Status: accepted (operator decision, 2026-11-21); implemented by INSTALL-001 (#207) and WF-09
- Date: 2026-11-21
- Supersedes in part: [ADR 0005](0005-authentication-and-sessions.md) (first-owner bootstrap
  channel); release decision 3 and the controller bundle's best-effort class in
  [scope-v1](../release/scope-v1.md); the "Application startup never migrates" data-safety contract
  there, which narrows as below; and the PORTABLE-COMPOSE-001 description, criteria 2 and 3, and
  the upgrade part of criterion 4.

## Context

The `v0.1.0-beta.6` portable installation needs three manual one-time commands before the stack can
start: create the PostgreSQL cluster, initialize the schema and create the owner. Upgrades need an
explicit paired backup and a manual `release_schema upgrade`. Each rule had a safety reason:

- the database must never silently start empty in place of existing data;
- an image update must never change data without a backup;
- the owner password must never appear in a Compose file.

Together they make Florabase harder to install than comparable self-hosted applications, which ship
one Compose file that a manager such as Dockhand deploys as-is. Operators also cannot use a Compose
manager alone, without a shell on the host.

The repository tracks fifteen Compose files: the build-based root `compose.yaml`, `compose.dev.yaml`,
nine workflow stacks (quality, quality network, integration, performance, review, UAT, UAT
instance, preview, sourcing), the controller bundle `deploy/beta/compose.yaml`, the portable
`deploy/portable/portable-compose.yaml` and two historical review stacks under `docs/review/`.
Contributors and agents cannot tell which file is authoritative.

## Decision

### One production Compose, self-initializing

The image-only portable stack moves to the root as `compose.yaml`, which becomes the only
production Compose file and the release asset. It replaces both the build-based root baseline and
`deploy/portable/portable-compose.yaml`. A Compose manager deploys it with no host commands other
than creating the data directory. The safety properties are kept by explicit one-shot services,
not by manual steps.

1. **Data directory and new-installation rule.** All data lives under one operator-created
   directory (`FLORABASE_DATA_DIR`), bound with `create_host_path: false`. The directory must be a
   subdirectory created inside the storage volume, never a mountpoint itself. Then a missing or
   unmounted volume makes the path absent and the deployment fails. A one-shot `prepare` service
   accepts the directory as a new installation only when it is completely empty. It creates the
   database and media subdirectories with their container owners and modes. The documented rule
   for operators is: create an empty folder inside a volume, never point the stack at a mountpoint.
   Pointing it at an existing empty mountpoint is the accepted residual risk.
2. **Installation marker.** The marker is a file in the data directory. It records the installation
   identifier, the PostgreSQL major version and the cluster system identifier. It is written
   atomically (temporary file and rename) only after the cluster and the initial schema both exist.
   Before PostgreSQL starts, `prepare` refuses:
   - a non-empty directory without a marker, including a crash between cluster creation and marker
     write (recovery: empty the directory and redeploy);
   - a marker whose database directory is missing or empty;
   - a marker whose PostgreSQL major version or system identifier differs from the cluster found.
3. **`migrate` one-shot service.** It runs after PostgreSQL is healthy and before the backend. It
   holds a PostgreSQL advisory lock, so concurrent runs wait or fail and never interleave. The
   backend depends on its successful completion.
   - Empty, unversioned database: initialize the schema to the image head.
   - Database at the image head: no change.
   - Database at the exact previous release head that the image declares (the existing
     `release_schema` rule): write `florabase-<from>-to-<to>-<UTC time>.dump` with `pg_dump -Fc` to
     the required `FLORABASE_BACKUP_DIR`. Then verify it with `pg_restore --list` and a non-empty
     table of contents, and upgrade. `FLORABASE_BACKUP_DIR` must be a separate path from the data
     directory, because a backup inside the data directory shares its failure domain. A missing or
     unwritable backup directory, or a failed or unverifiable dump, refuses the upgrade before any
     migration runs. Retention is the operator's.
   - Any other revision (newer, unknown, older than the previous release head): refuse, and nothing
     starts.
   - A failed or interrupted upgrade leaves the database off the image head. The backend then
     refuses to start, and the dump plus the paired backup are the recovery.
4. **The backend process itself still never migrates.** It keeps the exact-head schema guard.
   `depends_on` orders only a deployment. A later restart or a manual image change still meets the
   guard, which is intended. Schema changes still only come from reviewed Alembic migrations.
5. **First owner from the environment, once.** `migrate` creates the owner from
   `FLORABASE_OWNER_LOGIN` and `FLORABASE_OWNER_PASSWORD` only when no user exists. It uses the ADR
   0005 transactional single-owner constraint, so concurrent attempts create at most one owner.
   - A database that already has users, including one restored from a backup, never gets a new
     owner. The variables are then ignored, and a log notice says they can be removed.
   - If only one of the two is set, or the password fails the password policy, `migrate` refuses
     before creating anything. The message never contains the password.
   - If neither is set and no user exists, the stack starts, and the offline bootstrap and reset
     commands stay available.
   - The password is never logged, echoed or written outside the database hash.
6. **Paired backup is unchanged.** The automatic pre-upgrade dump protects the database against a
   failed migration. It does not replace the documented paired database and media backup, which
   stays the recovery procedure.

### Two Compose files in the repository

The repository keeps exactly two tracked Compose files: `compose.yaml` (production, image-only) and
`compose.dev.yaml` (development, standalone, source builds). Quality, integration, performance,
review, UAT, preview and sourcing stacks are derived from `compose.dev.yaml` at run time by the
workflow scripts. They use project names, environment, ports and generated override files under
untracked state, never tracked copies. The controller bundle (`deploy/beta/`), `deploy/portable/`,
the portable smoke's file references and the historical review stacks are removed or renamed when
their replacements land; git history keeps them.

## Consequences

- Release decision 3 changes: the official installation is the single self-initializing
  `compose.yaml`. The controller bundle is withdrawn instead of being kept as an advanced
  alternative.
- ADR 0005's rule that the first owner is never created from a Compose file is replaced by point 5.
  The accepted risk is that the initial password stays visible in the manager's stack environment,
  `docker inspect` and manager exports until it is removed. Mitigations: one-time use, a log notice
  and the documented password change at first sign-in.
- "Application startup never migrates" narrows to "the backend process never migrates". Deploying a
  new `compose.yaml` runs the guarded `migrate` service, which dumps before any upgrade.
  Per-feature statements that the application never migrates at startup stay true.
- On delivery, INSTALL-001 restates PORTABLE-COMPOSE-001, which keeps its delivered evidence. It
  also updates the documents that describe the current manual procedure: README, the installation
  and portable installation guides, deployment, security, versioning, the feature reconciliation and
  the CHANGELOG. Until then they correctly describe `v0.1.0-beta.6`.
- The release pipeline, publisher, portable smoke and their tests move to `compose.yaml` and must
  prove every case above.
- Workflow tooling (WF-09) must keep resource ownership, port allocation and cleanup guarantees
  while generating its stacks from `compose.dev.yaml`.
- The `v0.1.0-beta.6` manual procedure stays valid for that release. The first release with the new
  `compose.yaml` is the next beta.
