# BOTANICAL-IDENTITIES-VISUAL-001 refined visual review

## Candidate and boundary

Source: `/home/alessandro/.codex/worktrees/f6da/florabase`; branch
`feat/botanical-identities-visual-001`, base/HEAD `e7ade78559803a35b738a669085799f55eb76258`.
This second operator-requested pass preserves the first implementation, in the same managed
worktree. Feature status remains `implemented`. Operator acceptance and independent QA are pending.
No canonical FULL verification, receipt, staging, commit, push, PR, merge or delivery was performed.

[Current gallery](gallery.html) ·
[First-pass gallery](gallery-pass1.html) ·
[Refinement browser measurements](refinement/browser-evidence.json)

## Result and audit

| Area                | Refined behavior                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Directory rows      | Identities use the same 64px visual, 12px/16px padding, square internal row edges and inline name/cultivar grammar as comparable collection rows. Common name, actual counts and wrapping remain. Measured ordinary desktop rows: identity 92.53px, Seeds/Sowings/Plants/Harvests 89px, group 92.11px. Content determines final height.                                                                                                                                                                                                     |
| Selection           | One shared normalization rule applies the 3px inset semantic primary accent and primary-subtle background to comparable preview rows. Keyboard focus retains its separate outline, hover its existing treatment, and bulk selection its checkbox/wrapper. Audited Seeds, Sowings, Plants, Harvests, Suppliers, Orders, Locations and Identities; no unrelated directory workflow was redesigned. Live representative selection evidence covers Identities and the four core collection directories. The fixture has no Supplier/Order rows. |
| Header              | Scientific/cultivar/common name, image, breadcrumb, adjacent records and four main tabs remain. One labelled Add to collection menu exposes five distinct operations. Phone absent-cover layout is compact; the four main tabs fit one row.                                                                                                                                                                                                                                                                                                 |
| Overview            | Local reference excerpt/status, taxonomy linkage, five distinct linked record counts, active counts, one relationship-aware next action and four recent events. Metadata is disclosed separately. Counts include history; PlantGroups remain group records and Harvest counts do not imply stored remainder.                                                                                                                                                                                                                                |
| Collection          | One flat page, ordered Seed lots, Sowings, Plants, Plant groups, Harvests; two columns on desktop and one on phone. Each section shows at most four actual records, status/source context, contextual operation and exact filtered View all. A 40-record automated fixture verifies the bound; live seed preview shows four of eight.                                                                                                                                                                                                       |
| Reference           | One flat page: profile, taxonomy, botanical sources, structured native range, occurrence evidence. Heavy occurrence preview mounts only after explicit expansion. Dedicated map links retain exact identity context. Existing profile/range/source/media capabilities remain available.                                                                                                                                                                                                                                                     |
| Events              | Shared Journal timeline styles now belong to EventFeed instead of requiring the global Activity page wrapper. Dates, source labels, originating owner links, existing ordering and partial precision remain. Repetitive same-identity links are omitted in the identity context; long notes can expand without truncating stored text. Global Journal behavior is covered by the affected regression.                                                                                                                                       |
| Editor and deletion | Preserved contextual EditWorkspace, mounted Identity/Reference/Native range/Media drafts, section-specific saves, dirty/pending guards, native focus containment and return. Overview Danger zone retains Cancel-first confirmation and backend integrity enforcement. No deletion or editor save was submitted during this refinement review.                                                                                                                                                                                              |

The four main sections remain Overview, Collection, Reference and Events. Collection/Reference
read-only subtabs are removed. Existing `tab=seeds`, `sowings`, `plants`, `harvests`, `source`,
`taxonomy`, `native-range` and `occurrences` URLs resolve the appropriate main page and section
anchor. Main tab changes use browser hash navigation. Direct `tab=edit` remains supported.

## Exact navigation contracts

`{id}` is a stable Botanical Identity UUID, never a name-search surrogate.

| Destination            | Canonical URL                                        | Actual inclusion/filter layer                                                           |
| ---------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Seed lots              | `#/seeds?identity_id={id}&lifecycle=all`             | Exact `SeedLot.botanical_identity_id` in the existing complete-loaded directory filter. |
| Sowings                | `#/sowings?identity_id={id}&lifecycle=all`           | Exact actual `Sowing.seed_lot.botanical_identity_id`, not invented direct lineage.      |
| Plants                 | `#/plants?identity_id={id}&lifecycle=all&type=plant` | Exact actual Plant identity plus existing record-kind filter.                           |
| Plant groups           | `#/plants?identity_id={id}&lifecycle=all&type=group` | Existing Plants ownership/view model with distinct group kind.                          |
| Harvests               | `#/harvests?identity_id={id}`                        | Existing exact server filter over actual source relationships.                          |
| Return                 | `#/identities/{id}?tab=collection`                   | Visible Return to identity link in filtered core directories.                           |
| Native range workspace | `#/native-ranges?mode=species&identity={id}`         | Existing supported species selection.                                                   |
| Species distribution   | `#/species-distribution?identity={id}`               | Existing identity selection; loading occurrence evidence remains explicit.              |

Seeds, Sowings and Plants have complete-loaded APIs, without server pagination; the smallest
coherent change extends their existing client filtering layer. Search, lifecycle and record kind
compose with identity filtering. URL parser/serializer validate and canonicalize UUIDs, omit defaults,
restore on reload and follow Back/Forward. Visible filter chips and independent clear/reset actions
are provided. Saved Views preserve the exact filter through existing version-1 state.

Backend Saved View state validation adds optional UUID fields to SeedLotState and SowingState;
PlantState inherits the former. Existing JSONB storage requires no migration. Persisted API/database
round trips are covered by PostgreSQL integration tests. Backend OpenAPI and generated declarations
remain unchanged. This is an additive state contract, not a new list endpoint or search mechanism.

Journal and History have no safe established exact identity filter. No misleading filtered link is
shown. A follow-up must define event-time versus current-record identity inclusion and authoritative
History projection semantics before adding those filters. Identity Events remains the complete
existing linked-event view; it invents neither History facts nor Schedule occurrences.

## Creation and source eligibility

| Operation       | Canonical flow                                                                                                                                                                                                                                     |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Add seed lot    | `#/seeds?action=create&identity={id}`                                                                                                                                                                                                              |
| Add plant       | `#/plants?action=create&identity={id}&kind=plant`                                                                                                                                                                                                  |
| Add plant group | `#/plants?action=create&identity={id}&kind=group`                                                                                                                                                                                                  |
| Start sowing    | Explicit chooser of this identity's active SeedLots, then `#/sowings?action=start&seedLot={lot}`. Even one eligible source is confirmed explicitly; no source offers SeedLot creation.                                                             |
| Record harvest  | Explicit chooser of actual Plants/PlantGroups accepted by the current service, including inactive/history records; then `#/harvests?action=create&sourceType=plant\|plant_group&source={source}`. No source offers canonical Plant/group creation. |

Direct/acquired Plant and PlantGroup flows retain their existing lineage safeguards; active Sowing
rows also link to canonical from-sowing creation. Normal task activation retains the identity context
through `openCollectionPage`; modified clicks retain native link behavior. Menu-launched choosers
survive menu dismissal. Loading/retry/auth/abort and zero/one/many-source behavior are tested.
Quick Preview keeps its accepted first-pass six actions and responsive TaskDialog.

## Review environment and data preservation

Open **http://localhost:15176/#/identities**. The synthetic review account credentials remain in
the isolated review environment and are not included in the repository.

Exactly owned services: `florabase-botanical-visual-f6da-db-1`,
`florabase-botanical-visual-f6da-backend-1`, `florabase-botanical-visual-f6da-frontend-1`.
Their `io.florabase.source` label identifies the source above. Frontend loopback port is 15176,
backend 18176; PostgreSQL is not published. Network and database/media volumes use the same project
prefix. Existing migration head remains `20261013_0042`.

After host restarts, only positively owned services were resumed. The backend was recreated from
current source as `florabase-botanical-visual-f6da-backend:refined`, retaining original database/media
and network; its old stopped container is retained as `florabase-botanical-visual-f6da-backend-1-pass1`.
The foreign c902 Review environment/port 15174, other worktrees and DEV/UAT/Preview/production were
not taken over or reset. Before future lifecycle actions verify the exact source label again.

Original synthetic records were preserved. Six clearly labelled synthetic packets were added
(two active, two exhausted, two lost), with unknown quantity/provenance unasserted, plus the Saved
View **Refinement review · basil identity**. The basil fixture now has eight lots/four active, one
Sowing, one Plant, one PlantGroup and one Harvest. A second identity has a long cultivar and no
collection records. [Additions manifest](refinement/fixture-additions.json).
No original record was updated or deleted. Reference text remains explicitly synthetic.

## Evidence and checks

- Final affected frontend regression: **374 passed / 18 files**, 372.48s, single worker.
  [Machine-readable result](refinement/final-test-results.json).
  Selected App, UX001, UX004, directory-state/Saved Views, three core directories, Harvests,
  hub/reference/source actions, cover, EventFeed/global Journal and existing provider/map tests.
- Backend Saved View unit/service regression: **88 passed** (`pytest tests/test_saved_views.py
tests/test_saved_views_service.py --no-cov -q`). A non-fatal cache-write permission warning is
  recorded; assertions passed.
- PostgreSQL Saved View integration: **15 passed**, including all three persisted identity scopes,
  through `scripts/test-integration.sh tests/integration/test_saved_views.py`. Exact disposable
  project `florabase-integration-bf3889885f40` cleanup passed: two containers, one image and one
  network removed, zero residual containers/networks/volumes; shared build cache retained.
- Strict TypeScript and production build passed: **230 transformed modules**. Targeted ESLint
  passed all **30 changed TS/TSX files**, zero warnings. Scoped frontend Prettier passed.
- Backend Ruff lint/format passed all three changed Python files; strict mypy passed the changed
  state module. Backend OpenAPI export check and frontend generated declaration check passed;
  neither artifact changed.
- Feature graph: **112 valid features**. Whitespace, gallery local links and an empty staged diff
  checked. [Verification summary and exact selections](refinement/verification-results.json).
- **66 refinement screenshots / 63 measured states**, desktop 1440×844, tablet 1024×844,
  phone 390×844; zero measured root/body horizontal overflow. Original 71 screenshots retained.

No full repository test/lint pass or canonical FULL gate is claimed. Earlier first-pass full attempts
were interrupted (143), with ImportExport readiness failures in the full frontend attempt. An earlier
second-pass 512MB ESLint process exhausted its heap; the final unchanged selection passed at 1024MB.
No test timeout, assertion or validation was weakened. The final affected run emits jsdom's existing
unimplemented `window.confirm` diagnostic in an unrelated flow; editor guard assertions pass.

The gallery retains first-pass evidence separately and groups refinement captures by themes,
responsive sections, exact filtered destinations and operations. Measurements record actual viewport,
URL, selected tab and representative row dimensions/styles. Full-page captures are labelled. Captures
of older phone headers are explicitly labelled as preceding the final compact header adjustment;
the final phone Overview demonstrates that shared header adjustment. This distinction prevents
older screenshots being presented as final-source evidence.

The browser retained name/profile drafts across editor section changes. Its native discard dialog
then blocked subsequent automated interaction; the embedded dialog API returned no dialog handle.
No save was submitted. A fresh tab confirmed the persisted name/profile were unchanged, but final
phone recaptures and a new second-pass deletion screenshot could not complete. First-pass
Cancel-first deletion screenshots and final automated editor/delete regressions remain available.
Manual rejection/acceptance of the native discard prompt and final phone/header recaptures are
explicit independent-review items. No successful second-pass interactive deletion check is claimed.

## Limits and next review

All six delivered Botanical/Herbarium/Mineral light/dark variants use existing semantic tokens and
CONTROLS-001 controls. No global sidebar, Settings, palette or icon system was redesigned.
THEMES-001 and CONTROLS-001 status remains unchanged.

The fixture has no approved WFO snapshot, confirmed GBIF taxon or cached raster. Reference captures
show truthful prerequisites; no provider download was triggered. Automated occurrence tests cover
existing caching/missing-tile/provider behavior. Actual approved imagery, source-linked enrichment,
physical touch, assistive technology and zoom still require independent review. Botanical references,
native ranges, observed occurrences and recorded collection origins retain separate meanings.

Next: inspect the live hub and gallery, follow each View all and return link, review six themes and
responsive layouts, exercise source choices without creating unintended records, then check editor
discard/save/focus and Cancel-first deletion in an interactive browser. Obtain operator visual
acceptance before separately authorizing the canonical FULL gate and delivery.

Working tree intentionally unstaged and uncommitted.
`BOTANICAL_IDENTITIES_REFINED_REVIEW_READY`.
