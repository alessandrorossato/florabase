# ADR 0007: Accepted-name reconciliation, historical name retention, and duplicate-identity survivor contract

- Status: accepted
- Date: 2026-11-08
- Features: `TAXONOMY-001` (primary), `TAXONOMY-002` (name-history and search boundary)

## Context

`TAXONOMY-001` ("Add assisted accepted-name reconciliation / correction for BotanicalIdentity") and `TAXONOMY-002` ("Retain BotanicalIdentity synonyms and name history") require an operator to inspect advisory accepted-name evidence, review conflicts, and deliberately correct a `BotanicalIdentity` toward a currently accepted name without losing the name under which collection material was originally acquired or recorded, and without silently merging identities. Where duplicate-identity reconciliation is explicitly authorized, a designated survivor must preserve and transactionally repoint collection references.

A pre-mutation audit of the verified baseline (`ea4f3ad3`, migration head `20261013_0042`) establishes that **the existing schema cannot satisfy `TAXONOMY-001` without schema mutation**, and that **four consequential domain and database-constraint choices must be decided before writing an Alembic migration**:

1. **In-place overwrite in `botanical_identities`**: `BotanicalIdentity` (`backend/src/florabase/botanical_identities/model.py`) stores only `id`, `scientific_name`, `cultivar_name`, `common_name`, `created_at`, and `updated_at`. `PUT /api/v1/botanical-identities/{id}` overwrites `scientific_name` in place with zero historical retention.
2. **No per-holding acquisition-name snapshot**: `SeedLot` (`seed_lots`), `Plant` (`plants`), and `PlantGroup` (`plant_groups`) store only `botanical_identity_id` (`ON DELETE RESTRICT`). As noted in `docs/product-roadmap.md`, *"The current History projection uses current labels; historically accurate naming requires a dedicated design decision, not a claim that this evidence already exists. Name-retention design must inform TAXONOMY-001 before any mutation, even though TAXONOMY-002 delivery follows it in the graph."*
3. **Database immutability triggers block naive duplicate-identity deletion or evidence repointing**:
   - `native_range_applications` (`20261009_0039`) has `identity_id UUID NOT NULL REFERENCES botanical_identities(id) ON DELETE RESTRICT` and trigger `immutable_native_range_application BEFORE UPDATE OR DELETE`, which raises `'Native-range source evidence is immutable'`. Any duplicate `BotanicalIdentity` with an applied WCVP native-range proposal can neither have its `native_range_applications` repointed/deleted nor have its `botanical_identities` row deleted.
   - `native_range_proposals` (`20261009_0039`) has trigger `immutable_native_range_proposal BEFORE UPDATE`, which forbids repointing `identity_id` on historical proposals, and `ON DELETE CASCADE`, which would destroy reviewed proposal evidence if the losing `BotanicalIdentity` row were hard-deleted.
   - `operation_receipts` (`20260905_0016`, `20260907_0018`) stores `result_botanical_identity_id` under trigger `trg_operation_receipt_original_facts_immutable`. Repointing `plants.botanical_identity_id` or `plant_groups.botanical_identity_id` to a survivor causes `result.botanical_identity_id != receipt.result_botanical_identity_id` in `propagation/reversal.py` (`result_snapshot`), blocking propagation reversal with `result_structural_state_changed` unless explicitly governed.
4. **Heterogeneous external/local botanical sources and WCVP release drift**:
   - **WFO (`wfo_links`, `2026-06`)** links to either an `accepted` or `synonym` taxon; for a synonym, `evidence.classification[-1]` identifies the accepted WFO taxon (`source_taxon_id`, binomial/trinomial `scientific_name` without authorship, `rank`).
   - **WCVP (`wcvp_links`, `v15` default and `v16` optional)** currently restricts `confirm_link` to `eligible` (`Accepted`) taxa (`ENRICHMENT-001`), but `v15` and `v16` disagree on 4,299 status transitions and 10,929 accepted-ID mappings (`docs/wcvp-version-001.md`), and local WCVP search returns `Synonym` rows with `accepted_id` and `accepted_name`.
   - **GBIF / CoL XR (`external_taxon_links`)** caches `taxonomic_status`, `accepted_external_id`, and `accepted_name` (which frequently embeds authorship in `accepted_name`, unlike `BotanicalIdentity.scientific_name`).

---

## Phase 1 Domain Contract

### 1. Stable `BotanicalIdentity` UUID versus current accepted name

- `BotanicalIdentity.id` (UUIDv7) is the stable local concept handle referenced by collection holdings, profiles, media links, and source links.
- `BotanicalIdentity.scientific_name`, `cultivar_name`, and `common_name` represent the **current active display identity** in the collection.
- An accepted-name correction updates `BotanicalIdentity.scientific_name` (and `updated_at`) **in place on the existing `BotanicalIdentity.id`**. No collection FK (`seed_lots`, `plants`, `plant_groups`, `scheduled_activities`, `operation_receipts`, `record_media_links`, `botanical_profiles`) changes when an identity's name is corrected in place.
- Confirming or refreshing a taxonomy/enrichment source link (`wfo_links`, `wcvp_links`, `external_taxon_links`) **never** mutates `BotanicalIdentity.scientific_name` automatically.

### 2. Original acquisition name versus later corrected name

- Every `BotanicalIdentity` has an immutable **initial recorded name** (the `scientific_name` and `cultivar_name` under which the identity was first created) plus a chronological ledger of subsequent name states (`botanical_identity_names`).
- For material holdings (`SeedLot`, `Plant`, `PlantGroup`):
  - When an identity is corrected in place (`Identity A`: *Echinopsis lageniformis* → *Trichocereus bridgesii*), the identity's name-history ledger records that *Echinopsis lageniformis* was the active recorded name from `effective_from` until `superseded_at`, when it was superseded by *Trichocereus bridgesii*.
  - When a holding was originally created under a duplicate `BotanicalIdentity` (`Identity B`: *Cereus bridgesii*) that is later reconciled into survivor `Identity A` (*Trichocereus bridgesii*), the holding's **pre-merge identity and recorded name** must remain recoverable so the operator can see that the specific `SeedLot`, `Plant`, or `PlantGroup` entered the collection as *Cereus bridgesii* (`Identity B`).
  - See **Decision 1** below for the schema choice between holding-level `acquired_as` columns versus reconciliation-ledger attribution.

### 3. Source-scoped accepted names and synonyms

- Source assertions are **source-scoped and version-scoped**, never treated as universal truth:
  - **WFO (`wfo`)**: Scoped to confirmed `wfo_links.evidence.source` (`version`, `checksum`) or the active local WFO release (`2026-06`). When `wfo_links.evidence.taxon.taxonomic_status == "synonym"`, `evidence.classification[-1]` provides the WFO-accepted `source_taxon_id`, `scientific_name`, and `rank` (with full accepted-taxon `authorship` resolved from the local WFO index when available).
  - **WCVP (`wcvp`)**: Scoped to explicit release (`v15` or `v16`) and SHA-256 checksum. A confirmed `wcvp_links` record (`v15` or `v16`) or an exact-name lookup in the active WCVP index may report that the identity's current `scientific_name` or confirmed `external_id` is a `Synonym` of an accepted WCVP taxon (`accepted_id`, `accepted_name`) or has split/changed status across releases.
  - **GBIF / CoL XR (`gbif`)**: Scoped to `external_taxon_links` (`external_id`, `last_refreshed_at`). When `taxonomic_status != "ACCEPTED"` and `accepted_external_id != external_id`, `accepted_name` and `accepted_external_id` provide an advisory external suggestion. Because GBIF `accepted_name` may include authorship, the canonical binomial/trinomial must be validated or confirmed by the operator before applying to `BotanicalIdentity.scientific_name`.
- Former names and synonyms recorded in `botanical_identity_names` carry explicit provenance:
  - `status_kind`: `initial_recorded` | `former_accepted` | `merged_duplicate` | `source_synonym` | `operator_synonym`
  - `source_provider`: `wfo` | `wcvp` | `gbif` | `operator`
  - `source_version`, `source_checksum`, `source_taxon_id`, `accepted_source_taxon_id`, and `authorship` (nullable where `source_provider == "operator"`).

### 4. Conflicting WCVP versions and advisory source evidence

- All external and local reference datasets are **advisory**:
  - If WFO (`2026-06`), WCVP (`v15`), WCVP (`v16`), and/or GBIF disagree on whether the current name is accepted or propose **different** target accepted names, Florabase surfaces **all** source suggestions side-by-side and flags the conflict (`has_source_conflict = true`).
  - If a confirmed `WcvpLink` under `v15` is `Accepted`, while `v16` treats that same `plant_name_id` or `scientific_name` as a `Synonym` (or vice versa), both release states are shown with their exact release identifiers (`v15` vs. `v16`).
  - Florabase **never** auto-selects a winning source or auto-upgrades `v15` to `v16`. The operator must explicitly choose which suggestion (and source evidence snapshot) to confirm, or author a manual correction.

### 5. Historical-name preservation and attribution

- Every accepted-name correction is persisted atomically with:
  1. The superseded name state (`scientific_name`, `cultivar_name`, `common_name`, `effective_from`, `superseded_at`).
  2. The newly confirmed current name state.
  3. An immutable reconciliation evidence payload recording the confirming actor (`user_id`), UTC timestamp (`reconciled_at`), reconciliation kind (`accepted_name_correction` vs. `duplicate_identity_merge`), selected source evidence snapshot (provider, version, checksum, synonym taxon ID, accepted taxon ID, classification/rank), any conflict state that was present at confirmation time, and optional operator rationale/notes.
- No destructive rename is permitted: changing `scientific_name` without recording the superseded name state is prevented by the service contract.

### 6. Explicit distinction between correcting a name and merging duplicate identities

- **In-place Accepted-Name Correction** (`Identity A` → new `scientific_name` not used by any active `BotanicalIdentity` with the same `cultivar_name`):
  - Mutates `Identity A`'s `scientific_name` in place.
  - Preserves `Identity A`'s UUID and all collection links without moving any holdings.
  - If the target `(lower(scientific_name), lower(cultivar_name))` already belongs to another active `BotanicalIdentity` (`Identity B`), **the in-place correction endpoint refuses with `409 Conflict` (`code = "duplicate_botanical_identity"` and `existing_identity_id = Identity B.id`)**. It **never** silently merges `Identity A` and `Identity B`.
- **Duplicate-Identity Reconciliation (Merge)** (`duplicate_identity_id` → `survivor_identity_id`):
  - A separate, explicit decision and endpoint requiring the operator to inspect both identities, their holdings counts (`seed_lots`, `plants`, `plant_groups`, `scheduled_activities`), their profiles/native ranges, and their source links, and explicitly designate `survivor_identity_id` and `duplicate_identity_id` with concurrency tokens for both records.

### 7. Transactional survivor and reference-repointing rules when duplicate reconciliation is authorized

Every table and JSON projection referencing `botanical_identities.id` across the codebase has been audited:

| # | Referencing table / column | Current FK / constraint & triggers | Duplicate-merge action (`duplicate` → `survivor`) |
|---|---|---|---|
| 1 | `seed_lots.botanical_identity_id` | `FK RESTRICT`, indexed | Repoint all rows from `duplicate.id` to `survivor.id`; record repointed `seed_lot` IDs in merge receipt so pre-merge identity/name remains attributable. |
| 2 | `plants.botanical_identity_id` | `FK RESTRICT`, indexed | Repoint all rows from `duplicate.id` to `survivor.id`; record repointed `plant` IDs in merge receipt. |
| 3 | `plant_groups.botanical_identity_id` | `FK RESTRICT`, indexed | Repoint all rows from `duplicate.id` to `survivor.id`; record repointed `plant_group` IDs in merge receipt. |
| 4 | `scheduled_activities.botanical_identity_id` | `FK RESTRICT`, nullable | Repoint all rows where `botanical_identity_id = duplicate.id` to `survivor.id`. |
| 5 | `record_media_links` (`target_kind = 'botanical_identity'`, `target_key`) | `uq_record_media_links_asset_target`; trigger `record_media_link_identity_immutable` blocks `UPDATE` of `target_key`! | Because `record_media_link_identity_immutable` (`20261001_0027`) forbids updating `target_key`, insert new `record_media_links` for `survivor.id` (`ON CONFLICT DO NOTHING`, preserving `survivor`'s primary photo if one exists) and delete the `duplicate.id` links (or retain on tombstone). |
| 6 | `botanical_identity_cover_images.botanical_identity_id` | `FK RESTRICT`, `UNIQUE` | Keep `survivor`'s cover image if present; if `survivor` has none and `duplicate` has one, move `duplicate`'s cover image to `survivor` (and delete `duplicate`'s cover row if superseded, releasing the attachment only if unreferenced). |
| 7 | `botanical_profiles.botanical_identity_id` | `PK + FK CASCADE` (1:1) | Ensure `survivor` has a `BotanicalProfile`; copy non-null scalar/text fields from `duplicate` only where `survivor`'s corresponding field is `NULL` (refuse or require explicit operator resolution if both have conflicting non-empty text fields; see **Decision 3**). |
| 8 | `botanical_profile_native_ranges.botanical_profile_id` | `PK (botanical_profile_id, geographic_place_id)`, trigger `advance_native_range_revision` | Union `duplicate`'s native-range places into `survivor`'s profile (`INSERT ... ON CONFLICT DO NOTHING`), advancing `survivor`'s `native_range_revisions`. |
| 9 | `wfo_links.identity_id` | `PK + FK CASCADE` (1:1) | Keep `survivor`'s `WfoLink` if present; if `survivor` has no `WfoLink` and `duplicate` has one, either retain `duplicate`'s link on the retired tombstone or copy as stale/advisory (see **Decision 3**). |
| 10 | `wcvp_links.identity_id` | `PK + FK CASCADE` (1:1) | Keep `survivor`'s `WcvpLink` if present; retain `duplicate`'s `WcvpLink` on the retired tombstone if `duplicate` is soft-retired. |
| 11 | `external_taxon_links` (`(botanical_identity_id, provider)`) | `FK CASCADE`, `UNIQUE` | Keep `survivor`'s link per provider; move `duplicate`'s link only if `survivor` has none for that provider. |
| 12 | `native_range_proposals.identity_id` | `FK CASCADE`, trigger `immutable_native_range_proposal` (`BEFORE UPDATE` raises exception) | **Cannot be updated (`UPDATE` blocked by trigger)**. Retained intact referencing `duplicate.id` when `duplicate` is kept as a retired tombstone (`merged_into_id = survivor.id`). |
| 13 | `native_range_applications.identity_id` | `FK RESTRICT`, trigger `immutable_native_range_application` (`BEFORE UPDATE OR DELETE` raises exception) | **Cannot be updated or deleted (`UPDATE`/`DELETE` blocked by trigger, `DELETE` of `botanical_identities` blocked by `FK RESTRICT`)**. Requires `duplicate` row in `botanical_identities` to remain as a retired tombstone (`merged_into_id = survivor.id`). |
| 14 | `operation_receipts.result_botanical_identity_id` | No FK; trigger `trg_operation_receipt_original_facts_immutable` (`BEFORE UPDATE` raises exception) | **Cannot be updated (`UPDATE` blocked by trigger)**. `operation_receipts` keeps the original `result_botanical_identity_id = duplicate.id` fact. See **Decision 2** for whether `propagation/reversal.py` resolves `merged_into_id` equivalence or treats merge as a reversal-blocking structural change. |
| 15 | `saved_views.state` (JSONB) | No FK; `VIEW-001` contract | Unchanged; `VIEW-001` explicitly specifies that Saved Views retain stored filter UUIDs without background rewrites. |

### 8. Rollback, failure handling, and search implications

- **Concurrency & Optimistic Locking**:
  - Reconciliation endpoints require `identity_updated_at` (and, when confirming a source suggestion, `source_link_version` and `source_checksum`; when merging duplicates, both `duplicate_updated_at` and `survivor_updated_at`).
  - The service acquires `SELECT ... FOR UPDATE` on the target `BotanicalIdentity` row(s) in deterministic UUID order (`min(id), max(id)`) to prevent deadlocks.
  - Any version mismatch, stale source link, checksum drift, or newly introduced uniqueness conflict aborts the transaction before mutation and returns `409 Conflict` with structured detail.
- **Transactional Rollback**:
  - All writes (updating `botanical_identities`, inserting `botanical_identity_names` and `botanical_identity_reconciliations`, and—when merging—repointing holdings) execute in one database transaction. Any constraint or runtime failure rolls back all changes atomically.
  - There is no automatic "undo merge" command (consistent with Florabase's explicit compensation architecture in `docs/lineage-integrity.md`), though an in-place name correction can always be corrected again to a former or new name with full history preserved.
- **Search & Directory Implications (`TAXONOMY-001` & `TAXONOMY-002`)**:
  - Active `BotanicalIdentity` directories, pickers, and `/api/v1/search` return only **active (non-merged) identities** (`merged_into_id IS NULL`), preventing duplicate hits for retired tombstone identities.
  - Matching a historical/former name or synonym in `/api/v1/botanical-identities?q=...` and `/api/v1/search?q=...` resolves to the **active `BotanicalIdentity`**, exposing the matched former/synonym name in the summary so the operator can find material by its historical or synonymous name without treating every synonym as a separate `BotanicalIdentity`.
  - Direct `GET /api/v1/botanical-identities/{id}` on a merged identity either returns the retired record with `merged_into_id` so deep links can navigate to the survivor, or redirects cleanly in the UI.

### 9. Boundary between `TAXONOMY-001` and `TAXONOMY-002`

- **`TAXONOMY-001` scope**:
  - Foundational schema for historical name retention (`botanical_identity_names`) and reconciliation evidence (`botanical_identity_reconciliations`), designed so `TAXONOMY-002` requires no destructive schema rewrite.
  - Advisory accepted-name suggestion inspection (surfacing source evidence, version/cross-source conflicts, and collision detection against existing identities).
  - Explicit operator-confirmed accepted-name correction (preserving initial/former recorded names and provenance).
  - Explicit distinction between name correction (which refuses on collision with `409 Conflict`) and duplicate-identity reconciliation (with transactional survivor repointing if included per **Decision 2**).
- **Deferred to `TAXONOMY-002`**:
  - Standalone operator CRUD for adding/editing/removing arbitrary custom synonyms outside reconciliation.
  - Full multi-source synonym harvesting/import beyond the accepted-name reconciliation workflow.
  - Dedicated synonym-history management UI and advanced historical-name search badges across all collection surfaces.

---

## Accepted Design Decisions

The operator approved the following four decisions prior to schema mutation:

1. **Decision 1 (Option 1A — Identity-scoped name ledger + merge-provenance attribution)**:
   - Keep `seed_lots`, `plants`, and `plant_groups` schemas unchanged.
   - Persist `botanical_identity_names` (append-only historical & current name states per `BotanicalIdentity`, backfilled with `initial_recorded` from existing rows during migration) and `botanical_identity_reconciliations` (immutable evidence of every correction and merge, including the exact list of repointed `seed_lot_ids`, `plant_ids`, `plant_group_ids`, and `scheduled_activity_ids` and their pre-merge `BotanicalIdentity` snapshot).
   - Expose `original_scientific_name`, `original_cultivar_name`, `former_names`, and reconciliation history on `BotanicalIdentity` endpoints while `GET /api/v1/history` continues to project current display labels per `docs/operational-history.md`.

2. **Decision 2 (Option 2A-i — Both in-place correction and explicit survivor duplicate-merge using soft-retired tombstones `merged_into_id`; strict propagation-reversal snapshot invariance)**:
   - Add `merged_into_id UUID NULL REFERENCES botanical_identities(id) ON DELETE RESTRICT` and `merged_at TIMESTAMPTZ NULL` to `botanical_identities`, and scope `uq_botanical_identities_name_cultivar_ci` to active (`WHERE merged_into_id IS NULL`) identities.
   - When duplicate reconciliation is explicitly confirmed, transactionally repoint `seed_lots`, `plants`, `plant_groups`, `scheduled_activities`, `record_media_links`, `botanical_identity_cover_images`, and `botanical_profile_native_ranges` to `survivor`, while retaining the losing `BotanicalIdentity` row as `merged_into_id = survivor.id` so immutable `native_range_proposals`, `native_range_applications`, and `operation_receipts` triggers remain intact.
   - Leave `propagation/reversal.py` unchanged so strict propagation-reversal snapshot invariance (`result_structural_state_changed`) is preserved.

3. **Decision 3 (Option 3A — Survivor precedence with non-destructive union and profile conflict guard)**:
   - Native ranges (`botanical_profile_native_ranges`) and media links (`record_media_links`) union additively onto `survivor`.
   - Cover image and source links (`wfo_links`, `wcvp_links`, `external_taxon_links`): `survivor` retains its own confirmed link/cover if present; if `survivor` has none, `duplicate`'s link/cover is adopted (or retained on the retired tombstone).
   - `BotanicalProfile` text/scalar fields: if `survivor` has `NULL` and `duplicate` has a value, copy `duplicate`'s value; if **both** `survivor` and `duplicate` have non-null, differing profile fields, refuse the merge with `409 Conflict` (`code = "botanical_profile_conflict"`) unless the operator passes `profile_resolution = "keep_survivor"`.

4. **Decision 4 (Option 4A — Multi-source advisory suggestions + history-preserving `PUT`)**:
   - `GET /api/v1/botanical-identities/{id}/reconciliation` inspects confirmed `WfoLink`, confirmed `WcvpLink` and local WCVP `v15`/`v16` synonym/version-conflict evidence, and confirmed `ExternalTaxonLink` (GBIF), surfacing all advisory suggestions and any cross-source or cross-version conflict flags without auto-applying changes.
   - Ordinary `PUT /api/v1/botanical-identities/{id}` appends superseded `scientific_name` / `cultivar_name` states to `botanical_identity_names` (`source_provider = "operator"`), ensuring no code path can destructively overwrite a recorded botanical name.
