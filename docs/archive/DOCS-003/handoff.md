# DOCS-003 Handoff — Installation guide accuracy fixes and beta.8 publication record

- **Feature ID:** `DOCS-003` (`docs/features.json` status `implemented`; proposed release class `release-work` in `docs/release/scope-v1.json`, serving `DOC-01` / `G-DOCS`).
- **Branch:** `docs/docs-003-install-guide` from `origin/main` (`ddf5a1431453df6c6644fb1f2e9feeec6b120e16`).
- **Writer:** `antigravity-docs-003`.
- **Verification tier:** `docs` (Markdown/JSON under `docs/`, root `README.md`, and `CHANGELOG.md` `Unreleased` only).

## Part 1 — `docs/installation.md` (and `docs/backup-restore.md`) accuracy fixes

### 1. Paired backup (`docs/installation.md:251-289`, `docs/backup-restore.md:3-8`)

- **Before (`docs/installation.md:244-246`):**
  > In a Bash shell, from the folder with `compose.yaml` and `.env` (the same values the manager uses), set `project` to the stack name and run this as a block:
- **After (`docs/installation.md:253-259`):**
  > Over SSH in a Bash shell, run this block in the folder that holds the stack's `compose.yaml` (`docker compose ls` shows the stack's project name and config file path; Dockhand keeps its own copy of `compose.yaml`). If you want `release-manifest.json` archived with the backup, download it from the release assets of the deployed tag next to `compose.yaml` first; the block includes it when present and continues without error when it is absent. Set `project` to the stack name and run this as a block:
- Also updated `docs/backup-restore.md:4-5` to note that the release paired backup runs over SSH in the folder holding the stack's `compose.yaml`. Kept `project=florabase`.

### 2. `release-manifest.json` in the backup block (`docs/installation.md:255-287`)

- **Before (`docs/installation.md:264-266`):**
  ```bash
  cp compose.yaml release-manifest.json "$backup/"
  cd "$backup"
  sha256sum database.dump media.tar compose.yaml release-manifest.json > SHA256SUMS
  ```
- **After (`docs/installation.md:276-283`):**
  ```bash
  files=(database.dump media.tar compose.yaml)
  cp compose.yaml "$backup/"
  if [ -f release-manifest.json ]; then
    cp release-manifest.json "$backup/"
    files+=(release-manifest.json)
  fi
  cd "$backup"
  sha256sum "${files[@]}" > SHA256SUMS
  ```
- Explained that `release-manifest.json` is downloaded from the release assets of the deployed tag next to `compose.yaml`, and preserved `set -e` semantics for all commands while not failing when `release-manifest.json` is absent.

### 3. `FLORABASE_HTTP_PORT` removal and `restore-override.yaml` (`docs/installation.md:148-152, 300-322`)

- **Before (`docs/installation.md:144`):**
  > Forward your HTTPS hostname to `http://127.0.0.1:<FLORABASE_HTTP_PORT>` on the same host.
- **After (`docs/installation.md:148-149`):**
  > Forward your HTTPS hostname to `http://127.0.0.1:<port>` on the same host, where `<port>` is the host port of the `frontend` mapping (default `8080`).
- **Before (`docs/installation.md:281-300`):**
  `restore-override.yaml` only set `container_name`, and step 1 said `a distinct FLORABASE_HTTP_PORT`.
- **After (`docs/installation.md:300-322`):**
  Added `ports: !override` with `"127.0.0.1:8081:8080"` on `frontend` in `restore-override.yaml` (matching the `!override` syntax documented in `README.md:90` and `docs/deployment.md:19`), noted that overriding the port is needed only when restoring on the **same** host (and not needed on a different host, or can be edited directly in the restore copy of `compose.yaml` on Compose 2.20.1), and replaced `FLORABASE_HTTP_PORT` in step 1 with `a distinct host port for the frontend mapping (default 8080; needed only when restoring on the same host)`.

### 4. Data/backup folder names (`docs/installation.md:244-245, 390-393, 408-410`)

- **Before:**
  - `docs/installation.md:235`: `remove <FLORABASE_DATA_DIR>/state/upgrade-failed.env`
  - `docs/installation.md:363`: `| FLORABASE_BACKUP_DIR is inside FLORABASE_DATA_DIR (or the reverse, or the same) | Use a backup folder outside the data folder. |`
  - `docs/installation.md:365`: `| pre-upgrade backup failed / backup directory ... is missing or not writable | Fix the backup folder or free space and deploy again. Nothing was migrated. |`
  - `docs/installation.md:366`: `remove <FLORABASE_DATA_DIR>/state/upgrade-failed.env`
  - `docs/installation.md:382`: `florabase-backend mounts FLORABASE_BACKUP_DIR read-write`
- **After:**
  - `docs/installation.md:244-245`: `remove state/upgrade-failed.env inside your data folder (the left side of the /var/lib/florabase/data mount)`
  - `docs/installation.md:390`: `| the data and backup folders are the same / the backup folder is inside the data folder (or FLORABASE_BACKUP_DIR is inside FLORABASE_DATA_DIR) | Use a backup folder (the left side of the /var/lib/florabase/backup mount) outside your data folder (the left side of the /var/lib/florabase/data mount). |`
  - `docs/installation.md:392`: `Fix your backup folder (the left side of the /var/lib/florabase/backup mount) or free space and deploy again.`
  - `docs/installation.md:393`: `remove state/upgrade-failed.env inside your data folder (the left side of the /var/lib/florabase/data mount), and deploy again.`
  - `docs/installation.md:408-410`: `florabase-backend mounts your backup folder (the left side of the /var/lib/florabase/backup mount) read-write so its guarded start step can write pre-upgrade dumps without a separate migrate container`

### 5. § Synology NAS (`docs/installation.md:187-202`)

- **Before (`docs/installation.md:184-191`):**
  > The DS224+ is an amd64 target with Container Manager. Check the Engine and Compose versions it actually installs; Engine 24.0.2 and Compose 2.20.1 are the baseline.
  > 1. Run the folder setup block inside a local Btrfs or ext4 shared folder, for example `/volume1/docker/florabase/data` and `/volume1/docker/backup/florabase`.
- **After (`docs/installation.md:187-194`):**
  > The DS224+ is an amd64 target with Container Manager. Check the Engine and Compose versions it actually installs; Engine 24.0.2 and Compose 2.20.1 are the baseline. Backups, restores and the offline password reset need SSH access with the `docker compose` CLI on the NAS.
  > 1. Run the folder setup block inside a local Btrfs or ext4 shared folder, for example `/volume1/docker/florabase/data` and `/volume1/docker/florabase/backup`.

### 6. § Isolated restore on another host (`docs/installation.md:295-298`)

- **Added (`docs/installation.md:295-298`):**
  ```markdown
  On a normal Linux host (for example when running a restore drill on a laptop), the folder setup block needs `sudo` for `chown`, and because the production backend refuses a non-`https://` `FLORABASE_CANONICAL_ORIGIN`, a restore drill on another host needs an HTTPS origin too (see [Tailscale and HTTPS](#tailscale-and-https)).
  ```

### 7. § Upgrade automatic pre-upgrade dump condition (`docs/installation.md:235-237`, `docs/backup-restore.md:5-8`)

- **Verified against `backend/src/florabase/db/release_schema.py:501-517` (read-only):**
  ```python
  history = {revision.revision for revision in scripts.walk_revisions()}
  upgrade = (
      previous is not None
      and previous != head
      and previous in history
      and current == (previous,)
  )
  if not empty and current != (head,) and not upgrade:
      raise SchemaError(
          f"database revision {current or 'unknown'} is neither image head {head} "
          f"nor the previous release head {previous}; nothing was changed"
      )
  if upgrade:
      stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
      dump_path = dump(backup_dir, f"florabase-{previous}-to-{head}-{stamp}.dump")
      sys.stdout.write(f"schema-guard: pre-upgrade backup verified: {dump_path.name}\n")
      upgrading_dump = dump_path.name
  ```
  When `current == (head,)` (or `previous == head`), `upgrade` is `False` and `dump(...)` is not called.
- **Added (`docs/installation.md:235-237`):**
  > This automatic pre-upgrade dump is written only when the database revision changes; an image-only update (same Alembic head) writes none, so the paired backup in step 2 is the only recovery point.
- **Added (`docs/backup-restore.md:5-8`):**
  ```markdown
  ...and its `compose.yaml` also writes a verified dump before every schema upgrade when the database revision changes ([ADR 0008](decisions/0008-self-initializing-single-compose.md); image-only updates at the same Alembic head write none, so the paired backup remains the required recovery point).
  ```

## Part 2 — One-time folder setup prominence

- **`README.md:94-99`:** Added bold sentence linking directly to § 1 without duplicating owners or modes:
  ```markdown
  **Run the one-time [folder setup block](docs/installation.md#1-create-the-folders-and-set-owners-once) on the host before the first deploy.**
  ```
- **`docs/installation.md:19-21`:** Added 3-line callout at the top of the guide before `## What you install`:
  ```markdown
  > **Before you start:** Run the one-time
  > [folder setup block](#1-create-the-folders-and-set-owners-once) on the Docker host **before** the
  > first deploy. If the folders or their owners are missing, `db` and `backend` refuse to start.
  ```

## Part 3 — `v0.1.0-beta.8` publication record

- Created [`docs/release/evidence/beta-8-publication.md`](../../release/evidence/beta-8-publication.md):
  - Workflow run: `45124950700` (attempt 1, `2026-11-23T06:33:57Z` to `2026-11-23T06:49:37Z`, `success`).
  - Annotated tag `v0.1.0-beta.8`: tag object `3a6dc331ed0770cf24b171b4af650dbadda0585f` pointing to commit `c4ffd63004bf4448af902ffb9a012f5d53f965bd`.
  - GitHub Release `v0.1.0-beta.8` (`https://github.com/alessandrorossato/florabase/releases/tag/v0.1.0-beta.8`, published `2026-11-23T06:49:28Z`, `prerelease: true`, `draft: false`, `immutable: false`).
  - Downloaded assets & verified SHA-256 against Release API digests:
    - `release-manifest.json`: `32138ffea752d328c81c1cbd261c1ecd73064bd369436ffa2cbc1067a02c6b1c`
    - `RELEASE.md`: `2c3d2093afa30a2bb36c836395ff038a5813e2bd98ba9fc5549cfbde8217120f`
    - `postgresql-sbom.cdx.json`: `6bdc3abf3c571f91d40723cb932b2bf8b2857fef5452aa9b0e271fd902539129`
    - `florabase-0.1.0-beta.8-source.tar.gz`: `a82b1f343b31d62d7665ed4a1fcd79873925075980f2b3019194f30be5c84f00`
  - Image digests from `release-manifest.json` (and `compose_template.compose.yaml` `sha256:0c01356f0365bb13a601a8661fb9fdfc32ce24f1ea7a91515fdfb78bc2d62088`):
    - Backend: `ghcr.io/alessandrorossato/florabase-backend@sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee` (platform `sha256:e8fc8acd7a319cb2fa38648ceec4085dcc0533026984ac775b093bae1783c2c5`)
    - Frontend: `ghcr.io/alessandrorossato/florabase-frontend@sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8` (platform `sha256:7bb8229966f45bee5c7f6d2c6e59dbf819c9fb5e758aec80f065ba56f327495d`)
    - PostgreSQL: `ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.4@sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625` (platform `sha256:c677e9e20e56d6c32c2d359f66b44b66e2ead27d51fcaa64528f78a88299589d`)
  - Attestation output (`gh attestation verify`, GitHub CLI 2.105.0):
    - `release-manifest.json`: `Loaded digest sha256:32138ffea752d328c81c1cbd261c1ecd73064bd369436ffa2cbc1067a02c6b1c for file://release-manifest.json` / `Loaded 1 attestation from GitHub API` / `✓ Verification succeeded!`
    - `oci://ghcr.io/alessandrorossato/florabase-backend@sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee`: `Loaded digest sha256:1b63b75730cb11c5099f0280834ac974ac93db952c7ee1e6f676d09affc120ee` / `Loaded 1 attestation from GitHub API` / `✓ Verification succeeded!`
    - `oci://ghcr.io/alessandrorossato/florabase-frontend@sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8`: `Loaded digest sha256:15153404fd13a9db9a06e7401c751d63ff447a6a97ee9c7bab2b9214172290d8` / `Loaded 1 attestation from GitHub API` / `✓ Verification succeeded!`
    - `oci://ghcr.io/alessandrorossato/florabase-postgres:18.6-alpine-florabase.4@sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625`: `Loaded digest sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625` / `Loaded 1 attestation from GitHub API` / `✓ Verification succeeded!`
- Updated [`docs/release/scope-v1.md`](../../release/scope-v1.md#upgrade-baseline) lines 191–196 (§ Upgrade baseline) to link [`evidence/beta-8-publication.md`](../../release/evidence/beta-8-publication.md) and state that `v0.1.0-beta.8` (commit `c4ffd63`, Alembic head `20261110_0047`) is the current baseline.

## Follow-ups for next product batch (out of scope for `docs` tier)

1. **`compose.yaml` header comment:** Any desired prominence tweak in `compose.yaml` lines 1–4 was intentionally omitted here because touching `compose.yaml` escalates verification from `docs` to `full` (and affects `compose_template` SHA-256). Note that line 2 of `compose.yaml` already says `# Create the folders and owners once with the block in docs/installation.md before the first deploy.`; any further wording expansion belongs in the next product/full batch.
2. **`frontend/src/pwa/UpdateNotice.test.tsx` beta.7 fixture:** Updating the test fixture version string touches `frontend/src/pwa/` (`product-frontend` tier) and is deferred to the next product batch.
