# BETA-FOUNDATION-001 — v0.1.0-beta.1 acceptance contract

Audit date: 2026-11-02. Source baseline: `af2372c7e20468376b3d12904c83dee18133da84`
(current cached main, PR #139). This is an implementation/audit candidate for independent QA,
not a beta release approval. No production host was accessed or changed. No real collection was
imported. Proposed work below is not implemented by this increment.

## Evidence and interpretation

Reviewed the complete feature graph, roadmap and progress log; registered API routers and owning
services, corresponding React workspaces and focused tests; production/dev/preview Compose,
Dockerfiles, CI, health, backup/restore and worktree helpers. Paths below are repository evidence,
not a claim that every existing suite was rerun in this audit. Fresh execution evidence is in the
[QA handoff](beta-foundation-001-qa.md). Historic canonical runs in `progress.md` remain historical.

The roadmap's delivered-baseline section explicitly snapshots `f54648f` on 2026-10-13; later source
and merged progress take precedence for implementation presence. `features.json` statuses remain
unchanged for existing features: delivered code with `implemented` status is not silently promoted
to `verified`. A planned dependency such as EVENT-003 does not erase working structured Harvests.

Inventory terms:

- **D — delivered and usable:** source contains an integrated workflow and regression coverage;
  existing verified acceptance supports its bounded use. Real-host UAT still applies.
- **V — implemented, validate:** code/UI/coverage exist, but the feature's full acceptance or the
  actual-data/HTTPS/durable-host scenario remains unproven. This is not a missing implementation.
- **M — missing beta prerequisite:** the distribution or operating acceptance contract has no
  completed repository evidence. It may need packaging or a drill, rather than new domain code.
- **F — deferred:** explicitly outside the private single-owner beta; no prerequisite unless actual
  collection onboarding demonstrates a concrete need.

## Functional inventory

Backend paths below are under `backend/src/florabase/`; React paths are under `frontend/src/`.
Each integration test named below is under `backend/tests/integration/`.

| Capability | Evidence: owning source → UI → regression | Assessment and beta validation |
| --- | --- | --- |
| Species / Botanical identities | `botanical_identities/service.py`, `botanical_profiles/service.py` → `botanical-identities/BotanicalIdentityScreen.tsx`, IdentityCollectionHub → `test_botanical_identity_api.py`, `test_botanical_profile_api.py`, IdentityCollectionHub.test.tsx | **D** IDENTITY-001 / PROFILE-002 / BOTANY-002. Scientific name + cultivar represents identity; profiles and covers optional. Validate actual names, unknowns and duplicates without automatic reconciliation. |
| Taxonomy | `taxonomy/service.py`, `source.py` → TaxonomyScreen, TreeExplorer → `test_taxonomy.py`, graph/TreeExplorer tests | **D** TAXONOMY-003 / TAXONOMY-VISUAL-001, optional pinned WFO hierarchy and explicit confirmations. **V** production provisioning/mounts; **F** TAXONOMY-001/002 automatic reconciliation/name history and PHYLOGENY-001. No source means explicit unavailable state, not loss of collection. |
| Seed lots | `seed_lots/service.py` → SeedLotScreen → `test_seed_lot_api.py`, SeedLotScreen.test.tsx | **D** SEED-001–004. Separate physical lots, partial dates/quantity certainty, source, storage and lifecycle. Validate real packets and historical lots; do not merge packets by species. |
| Sowings / germination | `sowings/service.py`, `germination_service.py` → SowingScreen, GerminationSection → `test_sowing_api.py`, `test_germination.py` | **D** SOWING-001–003; **V** GERMINATION-001 remains implemented. Trial partial germination counts/dates and source consumption with actual notebook data. |
| Plants | `plants/service.py`, propagation/reversals → PlantScreen → `test_plant_api.py`, `test_propagation_api.py`, PlantScreen.test.tsx | **D** PLANT-001–006 and PROPAGATION-001–003. Individual tracking, lifecycle, extraction/transfer/reintegration and guarded reversals exist. Validate historical corrections and precision. |
| Plant groups | Same owning Plant/propagation services and workspace → `test_plant_transfer_migration.py`, `test_plant_reintegration_migration.py`, `test_propagation_reversal.py`, Propagation002.test.tsx | **D** counted groups and distinct individuals, with retained operation receipts. Group identity/count changes need real collection UAT; no new group mechanism needed. |
| Harvests | `harvests/service.py` → HarvestScreen → `test_harvests.py`, HarvestScreen.test.tsx | **V** HARVEST-001 remains implemented: ordered materials, exact one Plant/Group source, owned Event, partial date, shared media. Existing API/UI are present despite EVENT-003 remaining planned. |
| Stored material | `harvests/inventory_service.py`, `conversion_service.py` → StoredMaterial, ConversionDialog → `test_harvest_inventory.py`, `test_harvest_seed_conversion.py`, StoredMaterial/Conversion tests | **D** HARVEST-002/003: stock tracking, dispositions and explicit harvested-seed conversion with retained ancestry. Tracking and conversion are explicit; not every harvested item becomes stock automatically. Test depletion, unknown quantity, partial use, storage and conversion on real examples. |
| Suppliers | `suppliers/service.py` → SupplierScreen → `test_supplier_api.py`, `test_supplier_media.py`, SupplierScreen.test.tsx | **D** SUPPLIER-001–003: contact/source parties, retirement and shared media. Retired historical references persist. |
| Provenance | `provenance_sites/service.py`, `geographic_places/service.py`, lineage → ProvenanceSiteManager, provenance-map, IdentityOrigins → `test_provenance_site_api.py`, `test_lineage_api.py`, ProvenanceMap tests | **D** core provenance/geography and lineage; **V** GEOGRAPHY-003/MAP-001 UI statuses. Validate actual locality/accuracy and source precision. Supplier, current Location, origin and native range remain distinct. |
| Purchases | `orders/service.py`, `reconciliation.py` → OrderScreen, PurchaseContext → `test_orders.py`, `test_purchase_context.py`, PurchaseContext.test.tsx | **D** ORDER-001: transactions, optional exact total/currency/date, multi-lot links and explicit preview/apply acquisition choices. **F** accounting, SKU catalogue, pending receiving and allocated lot costs. |
| Locations | `locations/service.py` → LocationScreen, bulk move → `test_location_api.py`, `test_bulk_location.py`, `test_harvest_inventory.py`, ReferenceInteractions tests | **D** LOCATION-001 and bulk moves; **V** LOCATION-002/003 retain implemented status. Hierarchy, scopes, descendant usage and stored-material storage exist. Validate retired parents, physical naming and scoped moves. |
| Events / Journal / History | `events/service.py`, `history/service.py` → GlobalEventsScreen, EventJournal, HistoryScreen → `test_event_api.py`, `test_history.py`, `test_operation_receipts.py`, HistoryScreen.test.tsx | **D** EVENT-001/002, HISTORY-001 / ACTIVITY-001. History projects current authoritative facts, not an immutable security audit or historical-label ledger. Journal records past observations; structured flows retain owned facts. **F** generic deep event expansion EVENT-003. |
| Scheduling | `schedule/service.py` → ScheduleScreen, ScheduleCalendar, UpcomingActivities → `test_schedule.py`, calendar/Screen tests | **D** SCHEDULE-001/002 / SCHEDULE-UX-001: date-only tasks, targets, completion/cancellation, List/Calendar and Dashboard. **F** recurrence, push/email reminders and external calendar sync. Test local-day boundaries on the actual devices. |
| Media | `attachments/storage.py`, `media/service.py`, `copies.py`, `fetch.py` → MediaScreen, PhotosSection → `test_shared_media.py`, `test_shared_media_concurrency.py`, `test_external_media_copies.py`, MediaScreen tests | **D** protected attachment core / supplier integration; **V** ATTACHMENT-003–005 / MEDIA-VISUAL-001. Shared/unlinked originals, per-record links, primaries and saved external copies exist. Test real photo sizes/orientation, unlink vs delete and recovery of saved copies. External network failures must preserve valid content. |
| Authentication | `auth/` bootstrap/API/dependencies, `core/config.py` → `auth/`, App session restore → `test_authentication.py`, `test_transaction_lifecycle.py`, App tests | **D** SECURITY-002: owner password, Argon2id, server sessions, secure cookies, exact Origin and CSRF, throttling, default authenticated access. **M** real Tailscale HTTPS acceptance. Tailnet admission does not replace application authentication. **F** multi-user authorization/security sharing. |
| Import / export | `import_export/api.py`, `service.py` → ImportExportScreen → `test_import_export_api.py`, ImportExportScreen.test.tsx, [format contract](import-export.md) | **V** IMPORT-001 already implemented: UTF-8 CSV, six kinds (identities, suppliers, Locations, SeedLots, Plants, groups), templates/examples, row preview/choices and atomic apply. 2 MiB / 2,000-row limits. Not a Sowing/Event/Harvest/media import, update-sync or complete portable transfer. Real data shape is an onboarding question, not proof import is absent. |
| Search / maps / labels | search/explore/saved_views and label frontend → Dashboard, maps, LabelsScreen → `test_search002.py`, `test_species_distribution.py`, LabelsScreen tests | **D** supporting discovery, Saved Views, bulk moves and printable authenticated lookup. **V** physical label scans, actual mobile/keyboard use and optional providers. No mandatory online basemap. |

## Missing beta prerequisites and deferred product work

| Gap | Evidence / risk | Required disposition |
| --- | --- | --- |
| **M** published, paired application release | `compose.yaml` builds locally; `.github/workflows/ci.yml` verifies but has no GHCR publication. Both package versions currently say `0.1.0`; no accepted beta artifact manifest. | BETA-IMAGE-001 must publish and test backend/frontend from one accepted source, then record digests and coherent `0.1.0-beta.1` surfaces. |
| **M** image-only versioned Dockhand deployment | Baseline has sound runtime topology but requires checkout/build; no versioned beta stack or Dockhand deployment/upgrade contract is implemented. | BETA-RUNTIME-001. Keep existing dev/preview/operator workflows intact. |
| **M** repeatable recovery/upgrade orchestration | Existing paired backup/restore is substantive; isolated drill in backup docs is DB-only. No verified automatic app-upgrade state machine connects backup, quiescence, migration and release pair. | Reuse artifact validation, add durable release/revision/checksum evidence, full isolated restore, failure injection and controlled upgrades. Do not advertise Dockhand's container recreation as safe schema rollback. |
| **M** real collection acceptance | Synthetic fixtures/performance tests do not prove the operator's input quality or daily use. | BETA-DATA-001 rehearsal, then BETA-ACCEPTANCE-001 on the actual selected host. Manual entry may satisfy unsupported record kinds; add import types only if a measured blocker. |
| **M** continuously running host evidence | PERF-001 uses earlier source, synthetic tmpfs and loopback cookies. | Disk-backed soak, reboot, HTTPS, capacity, off-host backup and restore on the beta candidate. |

**F**: PWA/offline capture, richer event schemas, vegetative material modules, advanced lineage
visualization, botanical descriptions/traits blocked on sources, taxonomy reconciliation/name history,
weather/analysis, recurring care/notifications, collection sharing/multi-user isolation and full-fidelity
TRANSFER-001. None is necessary for this private single-owner beta. Required optional reference
sources must be provisioned if the operator chooses to use their workflows; their absence is otherwise
an explicit limitation. Visual redesign completion is not automatically a blocker; concrete inaccessible,
misleading or destructive behavior is. Existing accepted IA and beta workflows stay in scope.

## Smallest beta deployment architecture

**Proposed boundary:** one continuously running Linux Docker host, one private beta collection,
one PostgreSQL instance and local media volume, one paired backend/frontend release. No cluster,
shared network database, object storage or mandatory separate reverse-proxy product.

```text
Owner browser + Tailscale client
  → tailnet access rule → Tailscale Serve HTTPS :443 (host daemon)
  → 127.0.0.1:8080 frontend nginx (production image)
  → /api → backend (production image, UID/GID 10001)
  → PostgreSQL + backend-only media volume

Private operator → separately authenticated Dockhand → same host Docker
Release manifest → serialized upgrade controller → paired backup → migration → deploy → acceptance
Encrypted paired recovery set → independent off-host destination → isolated restore drill
```

Tailscale [Serve](https://tailscale.com/docs/features/tailscale-serve) provides tailnet-only HTTPS;
keep Funnel disabled for this installation. Restrict approved user/device access. Use one stable
`https://<node>.<tailnet>.ts.net` canonical origin; retain secure cookies, empty CORS and owner login.
Do not trust Serve identity headers as a Florabase session. Verify logout, expiry, Origin/CSRF and
binary access through HTTPS. Host-based Serve targets loopback; a containerized alternative needs a
separately tested network design. [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve)
documents persistent background configuration. Check daemon/Serve recovery after reboot and
certificate renewal; certificates disclose the hostname to [certificate transparency](https://tailscale.com/docs/how-to/set-up-https-certificates), so avoid
sensitive node names. No public database/backend/Dockhand ports.

Dockhand manages a **versioned image-only Compose document** with fixed project `florabase-prod` and stable named
volumes (`florabase-prod_postgres_data` and `florabase-prod_attachment_data`). Keep stack revision, backend/frontend digests, PostgreSQL version/digest and Alembic head
in a release manifest. Dockhand UI edits must not become an unrecorded second source of stack truth.
Use an approved immutable stack revision, no mutable `latest` application refs, source binds, Vite,
package installation or dependency volumes. Never silently adopt volumes from DEV/preview or change
the project name. Put secrets in protected host/Dockhand configuration; keep them out of Git, labels,
logs and command arguments. Back up Dockhand's own persistent state and credential encryption key;
it is an administrative control plane with Docker authority, separately protected from app users.

The [Dockhand manual](https://dockhand.pro/manual/) documents Git-stack deployment and image-update
recreation. This proposal uses its deployment management, **not** an assumed transactional migration
hook. Pin and test the chosen Dockhand release. Disable raw automatic container updates, unguarded
webhook deployments and Git auto-sync for this stateful stack. A serialized controller can select
approved release manifests automatically only after the safety contract below is implemented and
tested. Dockhand deployment must be an explicit step owned by that controller/operator; if the pinned
version cannot gate it reliably, beta ships with automatic checks/notifications and manual promotion.

### Host selection and resource envelope

No Synology model, Netcup plan, free capacity or uptime measurements were supplied. No host wins by
name. Prefer a Linux host with predictable local durable disk and recovery access. The following are
proposed screening budgets, **not measured minimums**: two CPU threads, 4 GiB available RAM for OS,
Docker, Dockhand, Tailscale and application headroom; 20 GiB free before collection media, retained
backups/reference datasets, plus growth/restore working space. Build images in CI, not on this host.
Confirm with the exact beta workload; a smaller host is acceptable only with measured headroom.

| Candidate | Strength | Constraints to prove before choosing |
| --- | --- | --- |
| Synology NAS | Existing durable local storage and potential backup tooling; collection remains at home | Exact CPU architecture/DSM/Docker Compose compatibility; spare RAM/IO amid NAS tasks; UPS and home connectivity; Docker permissions; separate physical backup; reboot/Serve and off-device recovery. [DSM7 Tailscale outbound behavior](https://tailscale.com/docs/integrations/synology) needs explicit checking for off-host backup paths. |
| Netcup VPS | Continuous datacenter host and remote recovery console may suit uptime | Actual plan RAM/CPU/disk and contention; persistent local disk and snapshot semantics; firewall/Tailscale-only exposure; off-provider backup, data locality, monthly cost and operator recovery access. Provider snapshots alone are not the paired restore proof. |
| Dedicated small Linux machine/VM | Conventional Docker/Serve operations and isolation | Always-on power, UPS/storage quality, uptime and separate backup destination; avoid an intermittently suspended development laptop. |

PERF-001 observed roughly 298 MiB combined application/DB working set on an older small synthetic
fixture, excluding this control-plane/OS envelope and durable IO. It cannot qualify today's host.
Optional WFO index is 413,069,312 bytes; WCVP v16 index is 952,799,232 bytes (see linked source
handoffs). Provision these explicitly with pinned hashes to read-only runtime paths, outside images
and originals storage; retain provenance and rebuild instructions in the recovery set. Production
Compose currently does not wire those settings/mounts. Measure thumbnails/media and restore staging
space; reserve room for two image pairs, dump + archive, restore staging, DB/WAL and retention.
For chosen volumes, use local filesystem semantics supported by PostgreSQL; do not place its live
PGDATA on an unvalidated network share.

### Startup, migration and health contract

Keep PostgreSQL 18's existing `/var/lib/postgresql` persistent mount and no published DB port.
Retain local media originals in the backend-only volume with UID/GID 10001 and restricted access;
verify fresh named-volume initialization and restart persistence using the published backend image.
Mount optional taxonomy/enrichment indexes read-only and configure their explicit runtime paths.

Startup order: healthy DB → **explicit one-shot Alembic operation from the target backend digest**
→ backend ready → frontend ready → authenticated HTTPS acceptance. A migration is never a side
effect of ordinary application startup. Compose supports health/success dependency conditions
([Docker startup order](https://docs.docker.com/compose/how-tos/startup-order/)), but those do not
quiesce an existing backend or back up data. The upgrade controller must do both first. Initial
installation must migrate before owner bootstrap; backend serving must wait for success. Do not let
an already-completed migration container from a previous release authorize a newer release.

Current `/api/v1/health` proves process liveness, `/api/v1/ready` checks database connectivity, and
nginx `/healthz` proves only frontend service liveness. None verifies Alembic compatibility, writable
media, authentication or a complete user workflow. Add explicit revision comparison and write/read
smoke to runtime acceptance, retaining distinct health semantics. A Compose unhealthy flag alone is
not recovery automation. Test DB-down recovery, process crash and host reboot; alert the operator
on sustained unready state, full disk, failed backup or failed upgrade. Bound container log growth.

### Backup, restore and upgrade safety contract

Reuse [paired backup/restore](backup-restore.md), `scripts/backup.sh`, `restore.sh` and
`backend/scripts/attachment_artifacts.py`: stop application writes; verify active original sizes and
SHA-256; dump PostgreSQL and archive original objects; validate both; preserve unlinked originals and
saved external copies. Thumbnails regenerate. Existing backup restarts backend on completion/failure;
an upgrade needs a controller-held quiescence boundary across backup, migration and deployment to
avoid a write gap. Do not compose commands casually and claim a consistent rollback point.

Proposed beta defaults, subject to operator acceptance: nightly off-host encrypted recovery sets
(**RPO ≤24 h**), additional paired snapshot before every upgrade, seven daily + four weekly sets,
and **RTO ≤4 h** demonstrated on the selected hardware/backup link. Off-host publication succeeds
only when both artifacts plus manifest/checksums are durably copied. Never expire the last verified
recoverable set. Alert on a missed backup; a stale/missing pre-upgrade set blocks promotion. Separate
protected configuration/secret backup includes canonical origin, volume mapping, image pair,
Alembic revision, optional dataset provenance and recovery credentials. Test restoration without
relying on the original host or registry availability; retain known-good image artifacts/access.

Restore acceptance uses an explicitly isolated destination (new project, DB/media volumes and private
port), restores **both** artifacts, compares revision/counts/relationships and all original digests,
then logs in and opens representative records and photos. Include unlinked assets, shared links,
saved external copies and stored-material/seed-conversion history. No source volume may be mounted
writable in the drill. A DB-only successful `pg_restore` is insufficient. Never test against real beta
storage. Before admitting new writes after disaster recovery, invalidate restored sessions through a
reviewed procedure and verify owner login; recovery sets contain authentication state.

Every application upgrade must serialize and retain a durable journal:

1. Resolve an approved same-source image pair + stack manifest. Pull both by digest and verify
   architecture, source revision, migration compatibility and available recovery/storage capacity.
2. Prevent overlapping Dockhand/manual deploys. Quiesce writers and keep them quiesced. Make and
   validate the paired pre-upgrade set; record previous/target images, revisions and checksums.
3. Run exactly the target migration in isolation from application writers. Unknown/ahead DB revision
   refuses before mutation. Failure keeps writes stopped and the previous recovery set intact.
4. Recreate both application services at their paired digests, without replacing PostgreSQL/media
   volumes. Check actual Alembic head, health, HTTPS login and media/domain smoke before unblocking
   writes. Record completion; interrupted runs resume the pinned target or require operator recovery.
5. On failure, notify once with the journal and explicit recovery choice. No blind retry loop,
   mutable-tag refresh, automatic `alembic downgrade`, volume deletion or automatic DB major upgrade.

| Failure point | Recovery contract |
| --- | --- |
| Pull/preflight fails, no migration | Keep known-good stack/data; remove no volumes. Retry only after diagnosing failure. |
| Application fails, schema unchanged and compatibility proven | Redeploy previous image pair/stack; check readiness, login and media before admitting writes. |
| Migration begins/fails, or succeeds but application fails | Preserve failed state for diagnosis. Prefer tested forward repair; otherwise restore the paired pre-upgrade DB **and** media into isolated replacement volumes with matching old images, validate, then explicitly switch. Do not assume old code supports new schema. |
| Failure after users resumed writes | Stop writers and assess post-snapshot changes. A restore loses later writes; require an explicit operator decision and preserve the failed data. No automatic rollback with silent data loss. |

Controlled automation is mandatory as a **bounded policy**, not unattended schema changes in beta. A
future scheduler may promote only approved manifests explicitly marked schema-compatible, with fresh
backup and the same tested controller gates; schema changes remain operator-approved until recovery
is proven. PostgreSQL and Dockhand/Tailscale upgrades have separate maintenance policies. A digest
pin prevents an image change unless the release manifest is deliberately updated
([GHCR digest selection](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)).

## Prioritized implementation increments

`features.json` is authoritative for dependencies/status/acceptance. These are the next bounded scopes;
no runtime/image mechanism is prebuilt in BETA-FOUNDATION-001.

| Order | Increment | Depends on | Required outcome |
| --- | --- | --- | --- |
| P0 / now | BETA-FOUNDATION-001 | AGENT-WORKFLOW-001 | Evidence inventory, beta contract/backlog and narrow retirement fix; independent infrastructure QA then canonical FULL before delivery. |
| P0 / next | BETA-IMAGE-001 | BETA-FOUNDATION-001, CI-002 | GHCR release pair, coherent beta versions, immutable manifest/source labels, image-only smoke and publication permissions/security. No deployment to a real host. |
| P0 / next | BETA-RUNTIME-001 | BETA-IMAGE-001, OPS-001, ATTACHMENT-005 | Versioned Dockhand stack and operator/controller procedures; durable DB/media, Tailscale HTTPS, optional sources, migration gating, paired off-host backup/full restore and failed-upgrade drills on isolated data. Select host from evidence. |
| P0 / before admission | BETA-DATA-001 | BETA-FOUNDATION-001, IMPORT-001 | Representative real-data format rehearsal in isolation, mappings/precision/count reconciliation, tested unsupported-kind manual entry and no unintended mutation. May proceed alongside image work. |
| P0 / release gate | BETA-ACCEPTANCE-001 | BETA-RUNTIME-001, BETA-DATA-001, SECURITY-002 | Owner-approved real-host acceptance, recovery/uptime/security checks and exact candidate FULL. Only then label v0.1.0-beta.1 usable for continuing collection work. |

**BETA-IMAGE-001 acceptance detail:** choose supported architecture from host screening; require native
amd64 image smoke, add arm64 only if selected host requires it and native smoke is available. Publish
backend/frontend production targets from one accepted revision with OCI source/revision/version labels,
locked dependencies, retained licenses/source obligations, minimal package-write permissions and no
secrets/dev/test caches or source-data indices in runtime layers. Do not publish arbitrary PR code.
Protect the release trigger; bind manifest to source and digests; retain previous pair and provenance.
Clean pull/run must prove non-root users, frontend proxy, explicit migration capability, health,
owner bootstrap and persistent uploaded media on disposable volumes. Test actual registry pulls,
not only local build tags. Producing a draft release artifact is not beta admission. Version bump
regenerates OpenAPI/TypeScript if exposed API metadata changes; no API drift exemption.

**BETA-RUNTIME-001 acceptance detail:** keep distribution Compose separate from dev overlays and
assert image-only configuration/no DB-backend exposure. Use stable volume identities and exact
replacement confirmation for restore. Exercise install → bootstrap → upload → restart/reboot →
backup → isolated restore → compatible app upgrade → migration failure → app failure after migration
→ interrupted upgrade recovery. Prove original/other environment identities unchanged. Validate the
pinned Dockhand API/deployment behavior before any automatic controller integration; manual gated
promotion is the fallback acceptance mode, not a fabricated hook. Keep application and infrastructure
updates separately controlled. Deliver a newcomer-readable installation and recovery runbook.

## Beta admission checklist and outstanding operator decisions

All items are mandatory before continuing real collection use; foundation readiness alone is not GO.

- Image pair/manifest and version surfaces identify one accepted candidate; local canonical FULL and
  protected release checks succeed. Existing implemented feature statuses are not blanket promoted.
- Disk-backed install/upgrade/recovery drills and production HTTPS security checks pass; zero data
  loss across ordinary restart/reboot. Media/private binaries remain authenticated.
- Representative actual-data scenarios cover identity → acquisition/provenance → SeedLot → Sowing →
  Plant/group → observation/schedule → Harvest → stored material → explicit SeedLot conversion;
  include unknown/partial quantities/dates, correction/conflict, sharing media and History navigation.
- Run a proposed seven-day ordinary-use soak (include one reboot and one planned application
  upgrade); record errors, backup successes, DB/media/image/log growth, memory/CPU/IO and login on
  desktop and phone. Acceptance needs explicit issue disposition; do not infer reliability from time.
- Demonstrated paired restore meets accepted RPO/RTO; independent encrypted backup destination and
  secrets recovery exist. Operator knows which writes would be lost after rollback.

Open decisions: exact NAS model/DSM or VPS plan and available CPU/RAM/disk; expected collection/media
size and source file formats; approved tailnet users/devices and stable hostname; selected architecture;
backup destination/key custody/retention and RPO/RTO; maintenance window and permitted outage; whether
optional WFO/WCVP workflows are required on day one. Defaults above permit planning but are not claims
about supplied hardware, subscriptions or operator acceptance. Public access and multi-user sharing
require a separate design.

## Retirement defect and correction

Original `retire()` checked `W_OK | X_OK` on **every** walked directory. POSIX removal of an empty
child uses write/search permission on its parent; a root-owned 0755 empty `frontend/node_modules`
therefore need not be writable itself. The reported historical directories are no longer present
in the managed root, so their original creation history cannot be forensically established here.
The dev layout (`./frontend:/app` plus nested dependency volume at `/app/node_modules`) supplies a
reproducible cause: Docker prepares the nested mount destination in the host bind as root, even
when the process uses a non-root UID. Stopping/removing the container removes the mount, leaving
an empty host directory. The volume-only ownership initializer does not change source ownership.

The correction checks writable/searchable parents and sticky-directory ownership, scans without
following links, keeps the write requirement on nonempty directories, and refuses mountpoints anywhere
inside the candidate using Linux mountinfo (including same-device bind mounts and escaped paths).
Unreadable/malformed/unavailable evidence refuses before Git unregisters anything. Retirement on
hosts without `/proc/self/mountinfo` now fails closed; no unsafe portability fallback. Symlink entries
are refused, including inside ignored caches. Ordinary ignored-cache allowlist policy is unchanged;
nonignored/unexpected content, dirty trees, finish proofs, writer/gate locks and owned Docker resource
guards still run. Git removal remains unforced. No chmod/chown/delete fallback was added.

This is a preflight under the existing cooperative workflow, not protection against a hostile process
changing mounts/files between inspection and Git removal. Operators must stop external writers. The
regression and real Docker smoke use disposable Git fixtures; no finished operator worktree was
retired by this task. Independent QA should review refusal-before-unregistration and repeat the smoke.
