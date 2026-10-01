# Structured Harvests — HARVEST-001

Harvest records material collected on one occurrence from exactly one Plant or PlantGroup.
It is historical information, not harvested-material stock. A retained inactive, dead, transferred,
reintegrated or reversed source is valid for recording past collection. BotanicalIdentity is derived
through the current source; no identity or Location FK is copied onto Harvest.

## Aggregate and correction contract

Harvest owns an optional label, existing `PartialDate` occurrence date, notes, at least one ordered
HarvestItem and one unique Event FK. Dates remain unknown, year, year/month or complete date. Without
an explicit label, the display title combines the source display name and up to two material kinds
(with “+ more” for additional kinds). UUIDv7 remains the stable identity; synthetic numbering is absent.

Each item has its own UUID, controlled material kind, optional description, optional quantity and
zero-based display order. The vocabulary is `fruit`, `flower`, `leaf`, `root`, `seed`, `stem_or_shoot`,
`whole_plant`, `other`. Description is optional for every kind, including Other. Items with the same
material kind are allowed when context differs. Aggregate writes accept 1–100 lines in list order;
corrections preserve submitted item UUIDs, reject foreign/duplicate IDs, remove omitted lines and
create IDs for newly added lines. There are no individual item mutation endpoints.

HarvestQuantity is deliberately small: positive whole `item_count` without a weight unit, or positive
`weight` in `mg`, `g` or `kg`. Values use Florabase's exact decimal-string serialization and PostgreSQL
NUMERIC, with an explicit `is_approximate` flag. An absent quantity means not recorded. Zero is not a
collection quantity; there is no remaining-stock or exhaustion meaning here. This does not reinterpret
SeedLot's seed-specific count/weight contract or build a generic measurements framework.

Creating and correcting a Harvest updates its items and owned `harvest` Event in one transaction.
The Event's Plant/PlantGroup target, partial date and notes match Harvest. Its API summary explicitly
exposes `harvest_id`, derived title and direct primary image. Summary/item edits therefore appear on
Event reads without copied material data. Owned Events cannot be edited/deleted through ordinary
Event APIs; use Harvest correction/deletion. Existing free-form harvest Events have no Harvest FK,
remain ordinarily editable/deletable, and are never inferred, migrated or rewritten.

Source corrections (including Plant ↔ PlantGroup) are ordinary historical corrections. They update
the Event target atomically and change the derived botanical context. Source lifecycle, Location,
PlantGroup quantity, source update timestamp and SeedLot inventory never change. Even Roots,
Whole plant and Seeds do not imply death, decrement, relocation or seed-inventory creation.

Plants/PlantGroups have no ordinary hard-delete endpoint; their retained history convention remains.
Harvest source FKs use RESTRICT, as existing Event references do. Database hard deletion of a referenced
source fails. Deleting Harvest removes its material lines and owned Event atomically. Its media links
are unlinked, clearing its primary, while shared MediaAssets remain in the library. Existing ordinary
Event-media semantics remain: independently attached Event media must be explicitly unlinked first.
No reversal/receipt workflow is introduced.

## Media, presentation and navigation

Harvest is the sixth concrete RecordMediaLink target and fourth explicit-primary target. It reuses
ATTACHMENT-005 APIs, record Photos UI, upload, external references, Link existing media, caption/order
editing and unlink. The same asset can be independently linked/primary on several records. Composite
foreign keys prove that a primary link belongs to that Harvest. Unlink clears that exact designation;
there is no automatic replacement. Shared originals, saved external copies, thumbnails, authorization
and opt-in external-image policy remain centralized.

The central RecordVisual resolves safe Harvest primary, safe source primary, eligible botanical cover,
then Harvest basket placeholder. A broken candidate falls through to the next. Remote external images
are not automatically loaded. Structured Harvest Events use this same resolution through their explicit
Harvest relationship, with no duplicated Event media links. Ordinary Event media behavior is unchanged.

Collection navigation places Harvests between Plants and Events; mobile exposes it through More.
Directory search covers title/source/identity, with Material and Source type filters. The backend also
supports literal text, material, source type, identity and exact source filters. Dates are not used for
misleading exact-range filtering. Desktop rows open a compact Quick preview with Open details primary
and Edit secondary; tablet/mobile open detail directly. Detail shows source/identity/date, material
lines, notes, owned Event/source-history links and shared Photos on one page without artificial tabs.

Record harvest is available in the directory, Dashboard Quick actions and both Plant/PlantGroup detail
headers (including historical sources). Contextual creation preselects the source. The form supports
searchable source selection, partial date, add/remove material rows, precision/unit controls, notes and
optional label. Controls have row-specific names; keyboard add/remove moves focus to a material control,
server row errors identify the line, and dialog Escape restores focus. A BotanicalIdentity's Collection
view includes derived Harvest history/count. Source Events already provide bounded journal filtering;
Overview is not flooded with another full historical list. Dashboard Recent activity and global Events
link to structured detail. Harvests are absent from Current holdings and analytics.

## Integrity, queries and migration

Revision `20261001_0029` follows external-copy revision 0028. It adds only Harvest/HarvestItem tables,
source/item/event constraints and indexes, a Harvest media target and explicit primary support. It
performs no network access and never modifies existing Event or media data. Populated downgrade refuses
to discard Harvest history; use the coordinated pre-upgrade database/content backup. Empty downgrade
and re-upgrade are supported by the canonical migration-cycle gate.

Immediate checks enforce source XOR, material vocabulary, quantity dimension/precision, date validity,
ordering and reference membership. Deferred PostgreSQL constraint triggers enforce ≥1 item at completed
transaction boundaries and coherent Event kind/target/date/notes, permitting valid atomic corrections.
Raw item mutations lock their owning Harvest to prevent concurrent last-line deletion write skew.
Application writes lock Harvest and source rows; media mutations reuse the target → asset → link lock
order. Database failures roll back the aggregate. No generic polymorphic FK or application startup
schema migration is used.

Directory projection joins source and identity once, fetches all material lines once and batches primary
summaries per target type. A populated 16-Harvest mixed-source/media test caps this at eight statements.
Detail filters that same projection to one Harvest. Event reads batch only Harvests owned by their
requested Event IDs; they do not read the whole Harvest directory. No per-row source, identity, item or
image lookup is introduced. Full-directory lists follow existing collection API conventions; pagination
and expanded global search are separate roadmap increments.

## Verification and operator review

The baseline `make check` passed 502 backend unit tests (90.89% coverage) and 327 frontend tests.
Focused Harvest/PostgreSQL verification passed 16 tests, including complete create/correction rollback,
wrong-target primary rejection, preservation of legacy Events/media and guarded/empty migration cycles.
The final canonical gate runs full unit/frontend/integration suites, formatting/lint/typing, API drift,
feature graph/workflow checks, production builds, migration cycle and whitespace validation. Its
complete result and exact-tree receipt are recorded in the final handoff without post-gate edits.
Unit tests cover vocabulary, explicit quantities, partial dates, normalization, aggregate validation,
atomic service writes, source correction, item identity, no source mutation, ownership and API rollback.
PostgreSQL tests cover relational corruption, source deletion guards, empty-aggregate rollback,
create/correct/delete, historical free-form Events, shared assets/primary/unlink, query bounds and
HTTP authentication/CSRF. Frontend tests exercise directory/preview, filters, detail/primary integration,
Plant and PlantGroup forms, multiple material lines, keyboard add/remove focus, partial dates, unknown
quantity, exact count, approximate weight, correction, validation and retry.

Rendered review uses the disposable `florabase-harvest-review` Compose project, isolated PostgreSQL
and media storage, synthetic long-name sources and an independently shared local image. Normal operator
volumes are untouched. The temporary review stack is removed after verification; screenshots remain
outside the repository.

| Viewport   | Reviewed behavior                                                                                                                                                                                                                  |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1440 × 844 | Directory and corrected compact Quick preview; creation/correction with multiple materials; detail, shared media, explicit primary/caption; contextual Plant/PlantGroup actions; Dashboard and global journal links/images         |
| 1024 × 844 | Directory-to-detail behavior; one/multiple-line controls and correction; detail/shared-media picker/upload form; contextual source selection; Dashboard/journal wrapping                                                           |
| 390 × 844  | Natural directory/detail scrolling, filters, single/multiple materials and labelled quantities; contextual creation; mobile media/primary controls; Dashboard/journal; long names, year/month/unknown dates and unknown quantities |

Keyboard Add material line focuses the new Material control; remove focuses the retained line. Cancel
and Escape restore dialog-trigger focus. Measured document widths remain within each viewport.
No horizontal overflow was found. Quick preview is intentionally desktop-only; tablet/mobile rows open
full detail. Existing shared-media upload/link/edit/primary controls are reused.

Operator acceptance is still required; HARVEST-001 remains `implemented`. This branch is kept unstaged
and uncommitted. No branch switch, commit, push, delivery, merge or feature-finish is authorized.

## Future pre-1.0 candidate: harvested-material inventory / disposition

A separate bounded contract may track remaining stored material, consumption, processing, discard,
gifting, propagation use, explicit conversion into SeedLot and storage Location. Harvested seeds now
record collection only. An explicit “Add to seed inventory” transition is future work. Shared MediaAsset
already permits future domain reuse; no stock, consumption, recipes, sales, orders, automatic state
mutation, custom vocabulary framework, workflow engine, analytics or Harvest-specific QR workflow is
implemented here.

## Exact changed files

Paths are relative to the repository root; all remain unstaged.

```text
README.md
backend/alembic/env.py
backend/alembic/versions/20261001_0029_structured_harvests.py
backend/openapi.json
backend/src/florabase/api/router.py
backend/src/florabase/collection_photos/model.py
backend/src/florabase/collection_photos/primary.py
backend/src/florabase/collection_photos/service.py
backend/src/florabase/collection_views/schemas.py
backend/src/florabase/collection_views/service.py
backend/src/florabase/events/schemas.py
backend/src/florabase/events/service.py
backend/src/florabase/harvests/__init__.py
backend/src/florabase/harvests/api.py
backend/src/florabase/harvests/model.py
backend/src/florabase/harvests/schemas.py
backend/src/florabase/harvests/service.py
backend/src/florabase/media/schemas.py
backend/src/florabase/media/service.py
backend/tests/integration/test_botanical_identities.py
backend/tests/integration/test_database.py
backend/tests/integration/test_harvest_migration.py
backend/tests/integration/test_harvests.py
backend/tests/integration/test_shared_media_migration.py
backend/tests/test_harvest.py
docs/architecture.md
docs/domain-model.md
docs/features.json
docs/harvests.md
docs/media-library.md
docs/product-roadmap.md
docs/progress.md
frontend/src/App.tsx
frontend/src/api/schema.d.ts
frontend/src/botanical-identities/BotanicalIdentityScreen.tsx
frontend/src/collection/DashboardScreen.tsx
frontend/src/collection/DashboardSearch.test.tsx
frontend/src/events/EventFeed.test.tsx
frontend/src/events/EventFeed.tsx
frontend/src/events/EventJournal.tsx
frontend/src/events/EventTargetPhoto.tsx
frontend/src/harvests/HarvestForm.tsx
frontend/src/harvests/HarvestScreen.test.tsx
frontend/src/harvests/HarvestScreen.tsx
frontend/src/harvests/api.ts
frontend/src/media/MediaScreen.tsx
frontend/src/media/targets.ts
frontend/src/photos/PhotosSection.tsx
frontend/src/photos/RecordVisual.test.tsx
frontend/src/photos/RecordVisual.tsx
frontend/src/photos/api.ts
frontend/src/plants/PlantScreen.test.tsx
frontend/src/plants/PlantScreen.tsx
frontend/src/styles.css
```
