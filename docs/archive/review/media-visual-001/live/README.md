# Media-owned populated Review

Actual application: **http://localhost:15280/#/media**.

Source: `/home/alessandro/.codex/worktrees/1d44/florabase`, branch `docs/media-visual-001`,
base `ee3487412fe458cbdf7145154c54a58b66132cae`. The frontend now includes the approved Media implementation; the backend is unchanged.
This is a real React/FastAPI/PostgreSQL Review, separate from the HTML proposal.

## Ownership and reproduction

Run from this worktree:

```sh
python3 docs/review/media-visual-001/live-review.py up
python3 docs/review/media-visual-001/live-review.py seed
python3 docs/review/media-visual-001/live-review.py status
python3 docs/review/media-visual-001/live-review.py check
```

The small adapter reuses `workflow_environment.Environment` validation, migration and exact running
source/volume/network guards. Only this process's project/port constants are specialized. Its temporary
copy of v4 specializes the same exact project, origin and database checks; no guard is disabled.
V5 is copied byte-for-byte. Canonical fixture files, production seed behavior and shared helpers remain
unchanged. Temporary runtime code is regenerated from the tracked helpers on every seed/check.

| Resource | Identity |
| --- | --- |
| Compose project | `florabase-media-review-1d44` |
| Role/source labels | `review` / this exact worktree |
| Public endpoint | `127.0.0.1:15280` only; canonical origin `http://localhost:15280` |
| PostgreSQL database and user | `florabase_media_review` in its own DB container; no published DB port |
| Backend | Internal only; ordinary application, no fixture adapter in request handling |
| Network | `florabase-media-review-1d44_internal` |
| DB/media/dependency volumes | Project-prefixed `postgres_data`, `attachment_data`, `frontend_node_modules` |
| Runtime/credential directory | `/tmp/florabase-media-review-1d44`, owner-only; no repository credential file |
| Owner login | `media-review` |
| Password reference | `/home/alessandro/.codex/visualizations/2026/10/26/01a178a5-efc1-7eb0-b477-aff58c5df561/media-review-access.json` (0600, outside served files); never publish contents |
| DB schema | `20261013_0042` |

No stop/remove/reset action is supplied. No foreign environment, retained standard Review volume,
DEV, UAT, Taxonomy, CI or production resource is adopted. `/dev/null` configuration avoids importing
production settings. One-off fixture containers are removed by Compose after execution; persistent
Review data stays. A failed/incomplete fixture refuses ordinary rerun rather than overwriting data.
If `/tmp` credentials are lost while the DB remains, do not regenerate a new owner/password or reset
the database; coordinate explicit recovery. Source/runtime changes after a database-ahead state need
normal migration compatibility handling, never a downgrade.

**Browser coordination:** local development auth cookies are host-scoped, not port-scoped. Another
Florabase `localhost` login in the same browser profile can replace this session. Coordinate login
batches or use separate browser profiles; do not change authentication to work around the audit.
Preferences are origin-specific. Viewport changes are checked in each capture.

## Fixture composition and evidence boundaries

Fresh v4 has 80 managed references; unchanged v5 adds 252 references. Media's separate additive
`.media-visual-001.json` ledger records 18 new assets, two record links and two cover references.
The first seed and repeat produced identical IDs, ledgers and counts. Repeat validates existing
references/content without resetting metadata, captions, ordering, primaries or credentials.

| Coverage | Actual values |
| --- | --- |
| MediaAsset rows | 35; two gallery pages at 24/11 |
| Protected local assets | 27; local-source pages at 24/3 |
| External-only references | 8; no stored external snapshot |
| RecordMediaLinks | 20 |
| Primary designations | 11; all owned by explicit eligible records |
| Identity covers | 2: one cover-only, one also linked as a secondary SeedLot image |
| Distinct botanical photographs | **8**, not 35 or 27 |
| Photographic asset rows | 10: eight v5 originals plus two deliberate cover-upload reuse cases |
| Synthetic drawings | 17: v4 generated leaf plus 16 clearly labelled calibration drawings |
| Calibration aspect ratios | Six landscape 640×480, five portrait 480×640, five square 512×512 |
| Shared photo / record gallery | Original Aloe photo on two actual same-Identity synthetic SeedLots; photo SeedLot has original primary plus independent cover-upload asset as secondary |
| Long title | Calibration 01 has an explicit wrapping/accessibility test title; existing v5 titles/attribution retained |

The extra cover assets are created through the existing cover upload service. They exercise current
behavior and are **not additional unique photographs**. There is no supported gallery-to-existing-asset
cover assignment. One cover upload is linked through the existing Media service; the other remains
cover-only. Neither cover designation nor unlink implies asset deletion. Separate link captions/order
and per-target primary flags remain intact. No taxonomic source or biological provenance is invented.

The calibration PNGs are deterministic geometric drawings marked “SYNTHETIC LAYOUT / Not a botanical
photograph” inside the image and metadata. They test long cards, geometry, pagination and locally
stored rendering. They cannot establish how a 35-distinct-photograph collection would feel. They
are generated directly by the fixture under recorded CC0 terms; no existing photograph is cropped,
recoloured, relabelled or multiplied to inflate photographic coverage.

The eight licensed botanical files, creator/source URLs, licence and modification notices come from
the existing [v5 manifest](../../../../scripts/fixtures/botanical-v5/media-manifest.json) and
[NOTICE](../../../../scripts/fixtures/botanical-v5/NOTICE.md). Cover reuse copies retain those same
credits and licences. Fixture ingestion uses existing decoder/storage validation and no network
download. External-only references remain unloaded until an explicit supported operation.

## Acceptance scope

`dataset.json` is actual server-service output with every asset's real references and eligibility;
`fixture-ledger.json` records initialization. Six negative checks reject DEV mode, standard Review,
global audit project, foreign source marker, foreign origin and foreign database identity.

Screenshots of the actual application are named separately from `proposed-*` screenshots. The earlier captures predate the implementation; new implementation captures are listed separately. The
4:3 grid and on-demand preview are implemented in the real React application. No CSS injection or mock screen is presented as
implemented application behavior. Physical touch, screen reader certification and actual browser
zoom remain separate from viewport resizing. Large original photography beyond v5's 640px files,
saved external snapshots and true high-volume photographic performance remain dataset limitations.

## Approved implementation access recovery

The original temporary password file disappeared. The operator explicitly approved changing only
the retained synthetic media-review owner password and revoking its four old sessions. The account
ID and all Media/collection data were preserved; no owner replacement, bootstrap or product auth
change occurred. Use the private access file above. If it is lost, require explicit operator
recovery authorization again; do not infer permission to reset an owner from up/status/seed.

Current implementation evidence is in ../implementation/; the earlier live/ captures remain history.
The final read-only asset comparison confirms all35 details/links/covers unchanged.
