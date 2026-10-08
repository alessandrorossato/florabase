# SUPPLIER-003 implementation handoff

Implemented Supplier imagery through the existing shared Media Library. Operator visual/product
UAT passed on 2026-10-05. Independent review found no production defect. Focused verification
evidences the acceptance criteria, and the feature graph marks SUPPLIER-003 `verified`. The
canonical gate and repository delivery complete the lifecycle.

## Worktree

- Path: `/home/alessandro/.codex/worktrees/73d8/florabase`.
- Branch: `feat/supplier-003-media`, attached with supported `make feature-init`.
- Base `origin/main` and current HEAD: `4dbf6cfa81840bf32a5dc029f7134e0035479fd4`
  (merged HARVEST-003, PR #69). Current main already contains ATTACHMENT-005 and SUPPLIER-002.
- Intentional unstaged changes: shared media model/services/contracts, Supplier summaries/UI,
  Media Library filters, one migration, focused tests, generated OpenAPI/TypeScript, domain/media/
  roadmap/feature/progress documentation and this handoff. No unrelated source changes.
- No extra worktree or primary checkout edit. Review data/screenshots and synthetic credentials are
  outside repository source. DEV was not operated.

## Domain

Supplier is a typed concrete `supplier_id` RecordMediaLink target. It accepts zero or many local or
external MediaAssets, with one optional explicit primary on a link belonging to that exact Supplier.
The global reusable asset has no category or Supplier-specific role. The existing shared primary
service and locking protocol support selection, replacement and clearing.

Every deliberately linked context has independent primary state. Unlinking the designated link
clears only its designation, without guessing a replacement or removing the asset/other links.
Supplier remains the direct acquisition source for SeedLot/direct Plant/direct PlantGroup; acquisition
and lineage never create media links or propagate imagery, primary state or BotanicalIdentity covers.
Orders, finances, botanical enrichment and global search are unchanged in scope.

## Media Library

The established Target control now offers All media, Collection media, Suppliers, Seed lots,
Sowings, Plants, Plant groups, Events and Harvests.

- Collection media: at least one explicit seed_lot/sowing/plant/plant_group/event/harvest link.
- Suppliers: at least one explicit Supplier link.
- Supplier-only assets are excluded from Collection media and Plant galleries.
- An explicit Supplier + Plant asset appears in Suppliers, Collection media and Plants.
- All media retains unlinked and cover-only assets. Linked/unlinked considers every record link.

A correlated EXISTS predicate composes with source kind, association, literal search and deterministic
created_at/id pagination. It never multiplies asset rows or totals. Listing uses two SELECTs (count
and page), independent of link multiplicity. Supplier record choices use two SELECTs and bounded
name/id pagination; labels are Supplier names, with retired state in choices, and URLs navigate to
`#/suppliers/<id>`. Media detail supports the Supplier primary context and existing caption/order/
unlink actions. The legacy `collection_link_count` API field counts all RecordMediaLinks; UI calls it
Record links, avoiding a breaking field rename.

## Supplier UI

Directory rows remain information-first: compact protected representative thumbnail or neutral
placeholder alongside name/type/direct-record summaries. Quick Preview uses the same shared visual
without acquisition-based imagery. Detail has a representative header visual and a Photos tab,
reusing PhotosSection for upload, external reference, link existing, caption/order, primary and unlink.
Media detail retains shared metadata and local-copy actions. Direct-detail edit now uses the loaded
Supplier detail even when there is no selected directory row.

Shared detail/tabs/action/dialog patterns remain intact. CSS changes only align Supplier directory
images and allow text wrapping. No separate Reference redesign or image-gallery directory was added.

## Integrity and privacy

Migration `20261005_0033` follows current main head `20261004_0032`. It adds nullable Supplier FKs,
exact-one-target checks, unique asset/Supplier and primary/Supplier constraints and exact-link composite
primary FKs. Supplier FKs restrict deletion; unlink cascade clears only a dependent designation.
The existing immutable-link trigger now protects all current target identity columns, including
Harvest and Supplier. Downgrade restores the parent function and constraints exactly.

No backfill, network fetch, binary copy or asset mutation occurs. Downgrade checks Supplier links and
primary designations before DDL and refuses populated history. Empty downgrade/re-upgrade and explicit
unlink followed by downgrade/re-upgrade preserve assets and collection links. Supplier has retirement/
reactivation and no ordinary hard-delete API; direct SQL deletion with links is restricted. Asset
deletion still requires zero links and zero identity covers.

Protected binary/thumbnail reads, authentication, owner mutation, CSRF, exact Origin, attribution,
licence and existing SSRF-safe copy fetching are reused. Reference-only external primaries return no
thumbnail and stay placeholders; explicit Preview once preserves browser disclosure. Saved external
copies use authenticated thumbnails; Save/Refresh/Remove local copy remain shared behavior.

## Performance

Supplier directory counts plus batched primary summaries use at most four SELECTs, regardless of
Supplier count (list, designation, local assets, external assets). The 30-Supplier mixed local/external
query-count test exercises that upper bound. Reference-only external summaries use three. Media
listing and Supplier choice counts are two SELECTs each. No lookup per Supplier or per asset was
introduced. Directory/Quick Preview and detail representatives use existing 320px protected thumbnails,
never eager full originals. PERF-001 was not rerun.

## Roadmap

SUPPLIER-003 is P1, category supplier, depends on SUPPLIER-002 and ATTACHMENT-005; operator UAT and
independent verification passed. The next milestone is the planned P1 infrastructure
feature PREVIEW-001: persistent isolated operator UAT Preview, Preview-only `preview / preview`
account and synthetic dataset, idempotent seed, explicit guarded reset and isolated workflow smoke.
Collection productivity v2 follows PREVIEW-001. BOTANY-003 stays planned on its parallel track with the approved WFO
incomplete TLS chain blocker; historical RELEASE-001 planning is retained.

## Verification evidence

All commands use this worktree's source. Backend checks used the supported isolated QUALITY profile;
frontend checks used the current-source Review frontend runtime without mutating its database.
Integration used task-owned tmpfs PostgreSQL project `florabase-supplier003-20261005`,
`compose.integration.yaml` and a read-only current-source override outside the repository.

| Check                                                                                                                                                                                | Result                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Focused backend pytest `--no-cov`: test_supplier, test_media, test_primary_photo, test_media_copies                                                                                  | 59 passed                                                          |
| PostgreSQL: supplier_media, supplier_media_migration, shared_media, shared_media_concurrency, primary_photo_concurrency, supplier_api, external_media_copies, shared_media_migration | 42 passed; 18 existing Alembic path_separator deprecation warnings |
| Focused Vitest: SupplierScreen, MediaScreen, PhotosSection                                                                                                                           | 27 passed across 3 files                                           |
| Selected App Supplier and UX-005 regressions                                                                                                                                         | 8 passed, 59 unrelated cases skipped                               |
| Ruff format and Ruff check                                                                                                                                                           | Passed                                                             |
| Strict mypy over src/tests                                                                                                                                                           | Passed, 256 files                                                  |
| Zero-warning ESLint and strict TypeScript                                                                                                                                            | Passed                                                             |
| API generation and `make api-check`                                                                                                                                                  | Passed; both generated artifacts included                          |
| Feature graph `python3 scripts/check-features.py`                                                                                                                                    | 88 valid features                                                  |
| Production `make build`                                                                                                                                                              | Backend and frontend images built                                  |

PostgreSQL coverage includes local/external sharing, primary replacement/clear/unlink, wrong-target/
duplicate/immutable link constraints, guarded deletion, no acquisition inheritance, query counts,
unique totals/pagination, search/kind/association composition, HTTP auth/CSRF/Origin, external-copy
privacy and both migration preservation paths. Deterministic race tests cover duplicate linking,
asset delete versus Supplier linking and primary replacement versus unlink.

Ordinary new-test type/lint/selector issues were corrected. Three existing App assertions now
wait for the actual lazy Reference screen and recognize Supplier names alongside the new image
accessible label; navigation, keyboard focus, forms, lifecycle and StrictMode dialog checks all pass.
Two existing integration assertions needed truthful updates: preservation now expects the additive
null supplier_id column, and retention copy now says record links. Their protection assertions remain
intact; the final matrix passes. An early
frontend command accidentally selected the entire suite, exhausted host RAM/swap and was interrupted
by stopping only its task-owned test container. That run is not passing evidence; focused tests were
rerun with `pnpm exec vitest run --configLoader runner`. No test configuration, timeout or threshold
was weakened. The canonical verification gate is the final local step after this independent review
and focused evidence.

## Feature Review and browser evidence

With explicit operator approval, the prior fbb6 Review was removed through its owning supported
`make feature-review-remove CONFIRM_REMOVE_REVIEW=florabase-feature-review`. Current
`make feature-review-up` and `make feature-review-status` report healthy frontend/backend/db,
live binds from 73d8, isolated Review DB/media/dependency volumes and code/database revision
`20261005_0033`, at http://localhost:15174. Review remains running for operator UAT.

Labelled synthetic examples A–G cover no media, one local primary, several media, external primary,
Supplier-only asset, Supplier + Plant asset and Plant-only asset. They are Review-only; no permanent
browser fixtures were added. The external reference uses example.test and is deliberately not a live
image provider. Successful remote preview/fetch is not claimed from that synthetic URL.

Completed browser checks:

- 1440×844: Supplier directory and Quick Preview show protected thumbnails/neutral absence; Supplier
  Photos controls and explicit primary replacement from shared F to Supplier-only E update the header.
- 1024×844: detail header and Photos layout inspected; DOM image sources are protected thumbnail URLs,
  320px natural width; document width equals viewport.
- 390×844: Supplier directory/detail inspected without horizontal overflow; Add external dialog focuses
  its first field, Escape closes it and restores focus to Add external.
- Reference-only external Supplier primary stays a neutral placeholder in the directory.

Screenshots are temporary local evidence, outside the diff:
`/tmp/supplier003-evidence/supplier-photos-1440.jpg`, `supplier-detail-1024.jpg`,
`supplier-detail-390.jpg`, and `supplier-directory-390.jpg` in that same directory.

The in-app browser later disconnected during high host load. Reconnection and creation attempts
reported no available browser, while Review services remained healthy. The operator subsequently
reported manual product UAT passed on 2026-10-05; that acceptance supersedes the earlier handoff's
pending-UAT status. The local browser interruption remains part of the evidence record and does not
claim that this agent completed the full browser matrix or a remote fetch from example.test. Review
remains available at the URL above.

Operator UAT subsequently passed. This handoff is superseded by the independent review and delivery
record here and in `docs/progress.md`.

## Subsequent ORDER-001 integration

Suppliers now lives under Sourcing. Supplier detail links to its exact filtered Orders directory;
transactions and totals belong to Orders, while existing Supplier/source/provenance/media semantics
remain unchanged. Retired Suppliers retain historical Order links. See [Orders](orders.md).
