# Shared media library — ATTACHMENT-005

Implementation on `feat/shared-media-library`; handoff boundary: **READY_FOR_VISUAL_REVIEW**.
This document supersedes the ownership/removal portions of the historical ATTACHMENT-003/004
contracts. No supplier or harvest capability is introduced.

## Inspected previous contract

The running model supported direct photos on SeedLot, Sowing, Plant, PlantGroup and Event, using
five concrete foreign keys. Supplier had no photo relationship. BotanicalIdentity had a distinct
one-current-cover relationship. LocalCollectionPhoto uniquely owned Attachment; external references
combined asset metadata with exact target and caption. Primary selection was separate and available
only on SeedLot, Plant and PlantGroup. Local removal previously removed its owned binary through
pending-delete retry. Target/source locks, cross-owner advisory guards, restrictive target foreign
keys, authenticated files and fixed 320px WebP responses already existed.

## Current contract

| Concept                       | Persisted responsibility                                                                                                                                                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `MediaAsset`                  | UUIDv7, local/external kind, one unique protected Attachment for a local original or optional external snapshot, canonical HTTPS image/source metadata, fetched_at, title, attribution/licence, optional dimensions, state, UTC timestamps |
| `Attachment`                  | Original key, filename, validated MIME, byte size, SHA-256, binary deletion state and creation timestamp; backend-only original file                                                                                                       |
| `RecordMediaLink`             | Asset ID, exactly one of the SeedLot/Sowing/Plant/PlantGroup/Event/Harvest target foreign keys, per-record caption, nonnegative display order, UTC timestamps                                                                              |
| `CollectionPrimaryPhoto`      | Exact SeedLot/Plant/PlantGroup/Harvest and selected local/external link ID; independent for each target                                                                                                                                    |
| `BotanicalIdentityCoverImage` | One exact identity, asset ID and matching source kind; a separate active reference                                                                                                                                                         |

The old local/external Python photo names are compatibility views over one link table. Asset fields
are forwarded to the associated asset; they are not copied into each relationship. Link identity is
immutable: reassociation requires unlink plus a new link. Composite foreign keys enforce asset kind
and exact primary target; a trigger also verifies the primary source kind. Per-target unique
constraints prevent duplicate `(asset, target)` links. Target deletion remains restrictive; Event's
existing delete action is blocked until its collection links are removed.

Primary is explicit. No upload, link, unlink or cover mutation guesses a selection or replacement.
The same asset can be primary for A and secondary for B. Unlinking A clears only A's designation.
Sowing and Event remain photo targets without a primary API. BotanicalIdentity remains excluded from
RecordMediaLink and uses its separate cover; Supplier and other target types are excluded.

### Retention and guarded deletion

Unlinked means **zero collection RecordMediaLinks**. Fully unreferenced means zero collection links
**and zero BotanicalIdentity cover references**. Both local and external assets may remain unlinked
indefinitely. A cover-only asset is unlinked, valid in the Gallery, and ineligible for deletion.

Gallery creation may create an unlinked asset. Record upload creates the new asset and record link
in one database transaction; a failure cleans only its newly written original. Removing the last
link retains the asset, original and thumbnail. Cover replacement/removal retains the former asset
and original. There is no age-based cleanup, link-count garbage collection or automatic purge.

Only **Delete media asset** can remove a fully unreferenced asset. The API returns 409 with both
reference counts while any link or cover remains. Local deletion commits asset and Attachment
`pending_delete`, hides content, removes its original and derivative, then removes metadata. Failed
storage cleanup remains visible in the Gallery as pending deletion and can be explicitly retried.
An unexpectedly missing active original reports 409 before the next retry completes. External asset
deletion also removes a saved snapshot and its derivative, using the same guarded lifecycle, and makes no network request. There is no cascade-unlink action.

### Concurrency

Link creation, metadata changes, primary selection and unlink use target → asset → link locks;
local primary selection additionally locks/validates Attachment. Concurrent target selections
serialize. Asset deletion locks the asset before counting references and touching the binary.
Database insert/update reference triggers lock that same asset and reject pending-delete media;
FK restrictions protect actual deletion, and a state transition trigger rejects pending deletion
while references exist. These guards also apply to direct SQL writes. Cover mutations lock the
identity and reference the asset under the same database guard. Link identity cannot change beneath
the discovery/locking sequence. Conflicts roll back and return actionable errors.

## API and compatibility

All reads require an owner session; writes require existing owner, exact-Origin and CSRF guards.
No API reveals original storage keys or paths.

| Operation                            | `/api/v1` route                                                                         |
| ------------------------------------ | --------------------------------------------------------------------------------------- |
| Gallery                              | `GET /media-assets` with query, kind, association, target, bounded limit/offset         |
| Detail / metadata / guarded deletion | `GET`, `PATCH`, `DELETE /media-assets/{id}`                                             |
| New local / external asset           | `POST /media-assets/local`, `POST /media-assets/external`                               |
| Paginated record choice              | `GET /media-targets/{target_type}`                                                      |
| Link existing                        | `POST /collection-records/{target_type}/{target_id}/media-links`                        |
| Link context / unlink                | `PATCH`, `DELETE /media-links/{id}`                                                     |
| Save / refresh external snapshot     | `POST /media-assets/{id}/save-local-copy`, `POST /media-assets/{id}/refresh-local-copy` |
| Remove external snapshot             | `DELETE /media-assets/{id}/local-copy`                                                  |
| Shared thumbnail                     | `GET /media-assets/{id}/thumbnail`                                                      |

Existing Photos, cover, content and primary routes remain available. Photo IDs now identify links;
photo/cover responses add `media_asset_id`, and photo responses add `display_order`. Legacy record
photo DELETE now **unlinks** and retains media. Legacy cover replacement/DELETE now changes the
cover reference and retains the former asset; the cover confirmation and success message make this
retention explicit. Direct Attachment DELETE remains guarded and forwards
fully unreferenced assets to the explicit media deletion lifecycle. Integrations must account for
these intentional removal semantics. OpenAPI and generated TypeScript declarations change together.

## User workflows and privacy

Open **Collection → Media**. Browse 24 assets at a time; search title, original filename or
attribution, and filter source, collection-link state or linked record type. Cards show source,
collection count and separate cover count. Desktop selection opens compact Quick Preview; opening
details shows the preview, technical/source metadata, links, captions, order and primary state.
Narrow screens open details directly. Detail supports editing shared metadata, linking one supported
record at a time, editing its context/order, selecting/clearing primary where eligible and unlinking.
Guarded asset deletion is visually separate and unavailable while references remain.

Record Photos offers **Add new media**, **Add external image** and **Link existing media**. Choose
one asset, supply record-specific caption/order, then explicitly designate primary if desired.
This copies no binary. Photos also links to media detail. Shared attribution is labelled as shared;
captions and order remain per record. Native controls and the existing trapped-focus PhotoDialog
provide keyboard navigation, Escape closing and return to the initiating control.

An **external reference** retains its canonical URL and attribution. **Preview once** explicitly
loads a remote image in the current detail/Photos view, with `no-referrer`; it stores no snapshot.
**Save local copy** explicitly fetches the image into Florabase's protected storage. The asset stays
external with the same UUID and references. A **local MediaAsset** remains a separate uploaded-image
kind; saving an external snapshot creates no second MediaAsset.

When a saved copy exists, Gallery, Quick Preview, record directories, Dashboard, Events, Photos and
identity covers use protected local content without contacting the external host. Cards distinguish
not stored locally from local copy saved; detail records the saved UTC date. **Refresh local copy**
explicitly fetches the canonical URL and replaces the snapshot and derivatives; a failed fetch,
decode or derivative preparation preserves the previous copy. **Remove local copy** confirms removal
of saved bytes only and retains URL, attribution, links, captions/order, primary selections and covers.
An absent copy returns to the existing external opt-in policy. BotanicalIdentity's acknowledged
Botany cover permission remains separate and never authorizes automatic remote loads in Collection.

### Fetch safety and snapshot concurrency

The backend fetches only for explicit Save/Refresh; metadata writes, reads and migrations never
fetch. Canonical creation retains its HTTPS validation. Each fetch/redirect accepts only HTTP/HTTPS,
rejects credentials/control characters/scoped addresses and resolves all destination addresses.
Any non-global, loopback/private/link-local/multicast/reserved destination is refused, including
mapped/transition IPv6. The TCP socket connects directly to the selected validated numeric IP;
TLS still verifies the original hostname and sends its SNI. DNS is not repeated at connection time.
No environment proxy, credentials, cookies, automatic redirect/retry or content decompression is used.
All redirects are revalidated, with three redirects maximum. DNS and the entire request/stream share
a 15-second deadline; a deadline timer shuts down the socket, including slow response bodies.
Responses are capped at the configured Attachment limit (25 MiB default), require JPEG/PNG/WebP
Content-Type, and then pass the normal signature/MIME, structure, full-decode, animation and pixel-bomb
checks. Fetch failures disclose concise public messages, without internal resolver/connection details.

Asset-row locks serialize save/refresh/remove/delete across processes. Copy endpoints run in request
worker threads so waiting for that lock cannot block a fetch's event loop. Validated new bytes and a
new derivative are finalized before committing the Attachment pointer swap. Old content is marked
pending deletion and retained by one durable `copy_cleanup_attachment_id` until cleanup completes.
The schema requires that cleanup attachment to differ from the currently published snapshot.
This is a retry marker, not media history. Explicit subsequent copy/deletion actions retry interrupted
cleanup; there is no background purge or age/reference heuristic. A removal publishes reference-only
state before deleting pending bytes; failures retain the cleanup pointer and can be retried. A crash
before the new pointer commits has the existing upload pipeline's documented inaccessible-file
recovery boundary. Versioned protected thumbnail URLs prevent a refresh showing a stale browser copy.

## Storage, queries and basic resource impact

Each local asset or saved external snapshot has one protected original and one regenerable WebP derivative, regardless of link count.
Original validation remains JPEG/PNG/WebP, 25 MiB maximum, existing trusted sharded storage and
symlink/path guards. Independent uploads are independent assets even when bytes match. The existing
safe renderer applies orientation, no upscale and a 320px maximum edge. Cache files live under the
backend's private `.thumbnails` directory, keyed by asset ID/digest/transform version. The asset lock
serializes first generation across workers and all three Gallery/photo/cover thumbnail routes.
ETags are private, vary by Cookie, and validate active content before conditional responses.
Uploaded originals, persistent external snapshots and PostgreSQL remain the paired backup; derivatives are disposable and regenerate after
restore. See [backup and restore](backup-restore.md).

Gallery uses two SELECTs independent of page size: total and paginated assets with grouped link/cover
counts. It returns counts rather than a linked-record graph. Detail uses batched target reads, at
most one per supported type, plus primary and cover queries; no per-link asset lookup. Record
choices use two SELECTs, with identity labels joined to the requested target; Harvest choices additionally
batch material-derived titles for the bounded page. Primary summaries
retain at most three batched queries; the empty case uses one. Regression instrumentation counts
SELECTs, excluding fixture savepoints and expired-object setup. Linking three records leaves one
original and one derivative; a 640×320 fixture renders 320×160 and repeated reads reuse its bytes.
The synthetic browser fixture stores originals of 4,715/5,484/4,793 bytes and derivatives of
1,140/1,192/1,752 bytes (320×192, 192×320 and 320×320 respectively). These are fixture
measurements, not real-photo compression guarantees. Unnamed record labels and picker options use
the trailing ID characters; UUIDv7 timestamp prefixes cannot distinguish nearby creations.
Frontend workspaces remain lazy chunks and grid/picker images use thumbnails with lazy decoding;
full originals load only on dedicated detail. This is basic evidence, not the later resource project.

## Migration and rollback

Alembic revision **20261001_0027**, parent `20260925_0026`, copies existing metadata into assets and
links without accessing or moving binaries. Existing local asset IDs use Attachment IDs; external
asset IDs use former reference IDs, and external-cover assets use cover IDs. Link IDs, exact targets,
caption and timestamps survive; primary IDs/source IDs/timestamps are untouched. Display order
preserves the previous chronological `(created_at, id)` order per exact target. Local cover and
external cover IDs remain, now referencing assets. Existing standalone Attachments become standalone
assets; a former linked/cover-owned original never becomes accidentally unreferenced. Existing
technical file metadata stays byte-for-byte intact. Legacy dimensions remain unknown until a later
explicit processing requirement; migration does no image decoding.

Revision **20261001_0028** adds optional fetched-at and durable pending-copy-cleanup metadata and
allows external assets to reference one Attachment. Existing external copies are absent. No migration
performs network access, moves files or creates references. Its downgrade refuses while external
copies/cleanup remain; explicit copy removal permits rollback to 0027. The 0027 populated-downgrade
guard and complete empty migration cycle remain in force.

A populated downgrade cannot represent shared links or retained assets in the old exclusive model.
It deliberately refuses while media metadata exists and requires restoring the paired pre-upgrade
backup. An empty-schema downgrade recreates the old photo/cover/primary schema; reupgrade is tested.
Take a coordinated backup before the explicit operator migration; startup never migrates.

## Verification and review evidence

Focused backend tests cover atomic upload/rollback, source and target integrity, independent
caption/order/primary, last-unlink retention, cover-only deletion guards, pending retries, thumbnail
reuse, HTTP auth/CSRF and bounded queries. PostgreSQL races prove duplicate linking, link/delete and
primary replacement serialization. A representative legacy fixture proves local files, multiple
photos, external metadata, primary, both cover modes, untouched no-photo records, standalone media
and guarded downgrade. Historical migration tests continue testing their own revision with explicit
legacy SQL rather than using today's ORM against an old schema. Frontend tests cover Gallery,
detail, picker, linker, upload, primary, caption/order, unlink/delete distinction and external opt-in.
External-copy tests cover persistence/read resolution, identity/link/primary/cover retention, byte and
derivative replacement, failed refresh, deletion/removal cleanup and recovery, pixel bombs, MIME/size/
timeout/redirect/IP validation, DNS pinning with hostname TLS verification, and PostgreSQL lock races.

The final `make feature-verify` result and tree receipt are reported in the handoff. It covers full
quality checks, backend/frontend suites, PostgreSQL integration, API drift, feature graph, workflow
helpers, production builds, empty migration cycle and whitespace. No coverage threshold, timeout,
assertion or runner setting is relaxed. Operator visual acceptance is still required.

### Rendered browser review

The isolated `florabase-media-review` Compose project used tmpfs PostgreSQL and synthetic images,
records and external example URLs; no normal operator volumes or media were touched.

| Viewport   | Rendered evidence                                                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1440 × 844 | Gallery: 29 assets, 24/5 pagination, local three-shape grid and compact preview; landscape detail with three distinct links; Photos primary set/clear                          |
| 1024 × 844 | Gallery opens dedicated detail; local grid; square/landscape detail; Photos and asset picker; record picker including Sowing; last collection unlink retains cover-only square |
| 390 × 844  | Natural scrolling Gallery/detail/Photos; local image containment; asset reuse with caption/order; record picker; wrapped actions; separate cover counts and blocked deletion   |

Search and source/all/linked/unlinked filters were exercised, including a cover-only asset in the
unlinked filter and an empty search. Native keyboard Escape closed pickers and returned focus to
the initiating control. The external detail initially had zero external `<img>` elements; explicit
opt-in to the synthetic inaccessible host showed Image unavailable. Delete confirmation was
inspected and cancelled; actual deletion/retry is proven by integration tests. Reviewed document
widths were 1440/1024/375 at the corresponding viewport widths, with no horizontal overflow.
Desktop compact preview was shortened during review so its detail action remains reachable.
Screenshots are provided with the operator handoff. This is implementation review evidence;
operator visual acceptance is still pending.

### External-copy rendered follow-up

The follow-up used two synthetic external references in the same isolated review project and a public
Python Software Foundation PNG as an explicit inbound fetch fixture. Save and Refresh succeeded
through the real pinned fetcher. The saved external asset retained its UUID, Plant link, caption/order
and primary selection. Reference-only and saved states were reviewed in Gallery at 1440 × 844,
1024 × 844 and 390 × 844; desktop Quick Preview shows the saved date. Detail separates Preview once,
Save, Refresh and Remove copy. Tablet/mobile removal confirmations were inspected and cancelled;
Escape restored focus. Actual removal, retry and byte cleanup are covered by integration tests.

DOM image sources in Gallery, Quick Preview, Plant directory/detail/Photos, Dashboard and Events were
protected `/api/v1` URLs, with no external image URL used to render the saved reference. Reviewed
page widths stayed within 1440, 1024 and 390 pixels respectively, with no horizontal overflow. Copy labels
stay concise; saved metadata and actions wrap naturally on mobile. Screenshots accompany the handoff.
Operator acceptance remains pending.

### Exact changed-file inventory

```text
README.md
backend/alembic/env.py
backend/alembic/versions/20261001_0027_shared_media_library.py
backend/alembic/versions/20261001_0028_external_media_copies.py
backend/openapi.json
backend/src/florabase/api/router.py
backend/src/florabase/attachments/service.py
backend/src/florabase/attachments/storage.py
backend/src/florabase/botanical_identities/service.py
backend/src/florabase/collection_photos/api.py
backend/src/florabase/collection_photos/model.py
backend/src/florabase/collection_photos/primary.py
backend/src/florabase/collection_photos/schemas.py
backend/src/florabase/collection_photos/service.py
backend/src/florabase/media/__init__.py
backend/src/florabase/media/api.py
backend/src/florabase/media/copies.py
backend/src/florabase/media/fetch.py
backend/src/florabase/media/schemas.py
backend/src/florabase/media/service.py
backend/tests/integration/test_attachment_api.py
backend/tests/integration/test_botanical_identities.py
backend/tests/integration/test_collection_photo_migration.py
backend/tests/integration/test_database.py
backend/tests/integration/test_external_media_copies.py
backend/tests/integration/test_primary_photo_api.py
backend/tests/integration/test_primary_photo_concurrency.py
backend/tests/integration/test_primary_photo_migration.py
backend/tests/integration/test_shared_media.py
backend/tests/integration/test_shared_media_concurrency.py
backend/tests/integration/test_shared_media_migration.py
backend/tests/test_attachment_service.py
backend/tests/test_attachment_storage.py
backend/tests/test_collection_photo_api.py
backend/tests/test_collection_photos.py
backend/tests/test_event.py
backend/tests/test_identity_covers.py
backend/tests/test_media.py
backend/tests/test_media_copies.py
backend/tests/test_media_fetch.py
backend/tests/test_primary_photo.py
docs/architecture.md
docs/attachment-004-review.md
docs/backup-restore.md
docs/decisions/0006-local-attachment-storage.md
docs/deployment.md
docs/domain-model.md
docs/features.json
docs/media-library.md
docs/product-roadmap.md
docs/progress.md
frontend/src/App.tsx
frontend/src/api/schema.d.ts
frontend/src/events/EventTargetPhoto.test.tsx
frontend/src/media/MediaEditor.tsx
frontend/src/media/MediaLinker.tsx
frontend/src/media/MediaPicker.tsx
frontend/src/media/MediaPreview.tsx
frontend/src/media/MediaScreen.test.tsx
frontend/src/media/MediaScreen.tsx
frontend/src/media/api.ts
frontend/src/media/helpers.ts
frontend/src/media/targets.ts
frontend/src/photos/BotanicalIdentityCover.test.tsx
frontend/src/photos/BotanicalIdentityCover.tsx
frontend/src/photos/PhotosSection.test.tsx
frontend/src/photos/PhotosSection.tsx
frontend/src/photos/PrimaryPhotoVisual.test.tsx
frontend/src/photos/PrimaryPhotoVisual.tsx
frontend/src/photos/RecordVisual.test.tsx
frontend/src/photos/RecordVisual.tsx
frontend/src/styles.css
```

HARVEST-001 extends supported record targets with Harvest and its independent explicit primary.
Harvest unlink/deletion retains MediaAssets; owned journal Events resolve Harvest imagery through
the aggregate relationship without duplicate media links. Supplier remains a separate future target.
See [Harvest media contract](harvests.md).
