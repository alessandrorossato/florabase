# EXPLORE-001 implementation handoff

Status: **verified**, operator visual/product UAT **passed**, independent review completed and
canonical `make feature-verify` **passed**. Authorized delivery and finish remain.

## Worktree

- Path: `/home/alessandro/.codex/worktrees/c6cd/florabase`
- Branch: `feat/explore-001-species-distribution`
- Base and unchanged HEAD: `de682031e9e0f490f326334d927c1c81269c7274` (ORDER-001, PR #76)
- Intentional implementation, tests, generated API, fixture and documentation changes are recorded
  in the reviewed feature commit.
  No primary-checkout source changes, screenshot artifacts, secrets or personal collection data.

## Representation

The complete audited lifecycle matrix is in [Species distribution](species-distribution.md).

| Domain | Authoritative identity | Living | Current | Historical evidence |
| --- | --- | --- | --- | --- |
| SeedLot | own BotanicalIdentity FK | No | active, including unknown quantity | all retained lifecycle values |
| Sowing | exact SeedLot FK → identity | No | active | completed/failed/abandoned/reversed retained |
| Plant | own BotanicalIdentity FK | active | active | terminal/reintegrated/reversed retained |
| PlantGroup | own BotanicalIdentity FK | active | active | terminal/reversed retained |
| Managed stored material | inventory → Harvest → exact Plant/PlantGroup | No | active, including unknown remainder | depleted retained |
| Unmanaged Harvest | exact retained source | No additional contribution | No additional contribution | already represented by retained source |

Historical scope requires no Current record anywhere. Living is a subset of Current; All represented
is Current plus Historical. Multiple records count once as an identity. Counts describe records,
not quantities or individual plants. Reference-only identities, scientific-name similarity and
recursive ancestry do not establish representation. Collection-produced SeedLots use their own identity.
No lifecycle, quantity, Location or native-range behavior changed.

## Local API and performance

Authenticated `GET /api/v1/explore/species-distribution/identities` accepts literal substring `q`
(maximum 200 characters), `scope=all|living|current|historical`, `offset=0..100000` and `limit=1..100`
(default 50). It returns bounded identity rows, filtered total and local occurrence-ready count.
Ordering is lowercased scientific name, cultivar (null first), then UUID. Grouped SQL UNION ALL
aggregation avoids duplicate rows and Python collection scans. Query-count regression proves two
SELECTs at both page sizes 1 and 50. Selected identity uses one local SELECT at `/{uuid}?scope=...`,
independent of search/page, with explicit mismatch or normal missing/unrepresented 404.

## Occurrence and privacy boundary

The workspace mounts the existing `OccurrenceMapPanel`; MAP-002 remains authoritative for summary,
quality/status policy, exact opaque Catalogue of Life XR identifier, density tiles, legend, attribution,
text companion and errors. The existing per-identity occurrence workflow remains available and gains
“View in Species distribution”. No new provider implementation, rematching, multi-species overlay,
occurrence persistence or native-range inference exists.

Opening, filtering, searching, selecting and opening Saved Views make zero provider calls. Explicit
Load requests normal MAP-002 evidence for one identity. A local confirmed GBIF link is available;
missing and unsupported-only links are separate explanatory states. Cached rank/status/refresh age
are not newly used as eligibility gates. Remote unavailability is discovered only after Load; zero
eligible records does not establish absence. Changing selection/search/scope or reopening the same
Saved View unloads the map. Provider errors leave local discovery usable with retry.

Only MAP-002's stored provider identifier, fixed checklist/status/quality parameters and tile
coordinates leave the backend. Collection UUIDs, labels, Suppliers, Locations and provenance do not.
The existing configurable direct basemap requests remain unchanged. No geolocation is used.

## URL, Saved Views and migration

`#/species-distribution?q=ocimum&scope=living&identity=<uuid>` stores only local stable state.
Default/empty values are omitted; invalid manual scope/UUID values safely fall back. The explicit
v1 `species_distribution` Saved View adapter persists `q`, `scope`, optional UUID `identity`.
Offset, map instance/zoom, response data, loaded/errors and other transient state are excluded.
Opening resets to page one and unloaded provider state, including same-identity reopening.
Refresh and Back/Forward restore local controls/selection. A selection outside scope remains visible
with an explanation and no Load; missing/no-longer-represented selection retains its UUID and clear
selection/view management. Search may exclude its row without substituting another identity.

Migration `20261008_0037` extends only `ck_saved_views_surface`. Downgrade locks writers and refuses
while Species distribution views exist, before replacing the constraint. PostgreSQL tests prove
refusal, preservation of another surface and compatible `0036 → 0037 → 0036 → 0037`.

## UI and review limits

Explore order is Botanical identities, Species distribution, Media, Geography, Collection origins.
The new route auto-expands Explore and is present in mobile More. Scope and row buttons expose
pressed state; selection has explicit text, keyboard-native buttons and a visible outline. Loading,
empty, missing-link, mismatch and error states are explicit; errors are announced. Desktop uses two
columns; at 850px and below the workspace follows natural vertical flow. Long labels wrap.

Operator UAT **passed**. Independent spot review confirmed the authenticated UAT route displays the
expected four identities and one occurrence-ready link, and the narrow viewport uses vertical flow
with the long cultivar wrapping. The operator acceptance covers the full product workflow. Automated
MAP-002 and workspace tests cover explicit-load, error/retry, zero eligible, attribution, quality policy
and navigation behavior. No screenshot files were saved; no live provider data was included in the
fixture.

## Independent review and verification

- Independent final review found no production behavior defect. Exact relationship derivation,
  lifecycle boundaries, bounded two-query projection, explicit one-identity MAP-002 loading, provider
  privacy, canonical state and `0037` downgrade protection match the approved contract.
- Canonical `make feature-verify` passed: **797 backend unit tests** at **90.06% coverage**, **508
  frontend tests**, **662 isolated PostgreSQL integration tests**, feature graph (**94 valid**),
  workflow guards, Ruff/Prettier/ESLint, strict mypy (**299 files**), strict TypeScript, generated API
  drift, both production image builds, migration cycle `0036 → 0037 → 0036 → 0037`, whitespace checks
  and a working-tree verification receipt.
- PostgreSQL integration and migration-cycle tests used disposable databases; the integration project
  cleaned its own resources. Existing Alembic path-separator deprecation warnings remain.
- Operator UAT passed before independent review. No product change was needed after UAT.

## Ready UAT

- URL: **http://localhost:15174/#/species-distribution**
- Synthetic credentials: **preview / preview**
- Guarded owner: this worktree. The old `3558` preview was retired with the supported removal command
  after explicit operator approval; this worktree ran `uat-preview-up`, seed and status.
- Fixture v3 has **38 baseline records**; repeated seeding succeeded unchanged. DEV, Stable Preview,
  Feature Review and production were not modified.
- Four represented identities: basil and aloe Living; lavender Current but not Living; long-cultivar
  radish Historical only. `Viola tricolor` is reference-only and excluded. Counts: All 4, Living 2,
  Current 3, Historical 1. Basil alone is locally occurrence-ready.
- Basil's reviewed real CoL XR identifier is **48GBK**, `Ocimum basilicum L.` (accepted species,
  Plantae/Lamiaceae/Ocimum). It was verified through the existing provider on 2026-10-08 and seeded
  through the existing confirmation service with an offline reviewed snapshot. Seeding does not call
  providers, fabricate occurrences or infer a relationship by name.

Recommended scenarios:

1. Check all four scopes and reference-only exclusion; search scientific/common/cultivar text.
2. Select basil and verify no external evidence until explicit Load; then inspect density, legend,
   attribution, accessible summary, retry and current provider availability.
3. Select aloe/lavender/radish: useful no-link explanation and BotanicalIdentity details navigation.
4. Save Living + basil, load evidence, reopen the view: selected local state restored, page one,
   provider unloaded. Exercise refresh and Back/Forward.
5. Check a stale-scope selection and clear action; use the long radish cultivar at all three widths.
6. Review keyboard focus, mobile More, all controls, map/attribution and horizontal overflow at
   1440×844, 1024×844 and 390×844. Reconfirm occurrences do not establish native range and Collection
   origins remains a separate destination.

## Roadmap and next owner

EXPLORE-001 is `verified` after operator UAT and independent canonical verification. The reviewed
feature commit is ready for protected delivery and local finish. Preferred next product increment
after delivery is **EXPLORE-002 — Native ranges**, a separate reviewed structured-range/geometry
contract; no geometry, aggregation or navigation for it was implemented. **SCHEDULE-001** remains
future Activity work. **BOTANY-003** remains blocked and unchanged.
