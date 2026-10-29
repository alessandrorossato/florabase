# Integration and environment ownership

Checked against fetched `origin/main = ee3487412fe458cbdf7145154c54a58b66132cae` on 26 October 2026.
Older handoffs describe candidate checkpoints; current Git delivery evidence takes precedence.
The feature registry still marks several delivered capabilities `implemented`. This audit does not
mass-edit their statuses or reinterpret that as an unmerged branch.

| Workstream           | Baseline evidence                                                                                 | Boundary / incremental review                                                                                                                                                                                                                                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CI-004               | #125 `c570d0a`, ancestor of audit HEAD                                                            | Delivered verification workflow; do not reimplement or run a canonical gate for audit docs.                                                                                                                                                                                                                                                       |
| Taxonomy             | #126 `ee34874`, audit HEAD; `TAXONOMY-VISUAL-001` verified                                        | Delivered graph and accepted final interaction remain owned by Taxonomy. Current audit covers missing-WFO fallback. Next integration is configured-source graph/fullscreen/KPI evidence on delivered main, not another architecture redesign.                                                                                                     |
| Geography            | #122 `3902b92` plus earlier Maps #116/#118/#119                                                   | Canonical Geography six-route hub and three evidence contracts delivered. Do not recreate the removed Maps subgroup or automatically load occurrences.                                                                                                                                                                                            |
| Botanical identities | #121 `5778da7`                                                                                    | Delivered hub, exact collection drilldowns and separately saved editor sections retained. Excess surface nesting is explicitly accepted visual debt; propose bounded later normalization.                                                                                                                                                         |
| Harvests / Locations | #113 `9a73d3f`, ancestor of current main                                                          | Use delivered implementation and local handoff; preserve collected vs stored stock, physical hierarchy/scopes, unknown quantities and contextual edit. No candidate code copied.                                                                                                                                                                  |
| Sourcing             | #117 `4a657d8`, current main history                                                              | Reviewed Suppliers/Orders workflows delivered. Reconciliation, unknown Supplier/price, precise forms and safe picker query behavior retained. Sourcing Preview remains untouched.                                                                                                                                                                 |
| Themes / Controls    | #120 `e7ade78`, delivered before current audit                                                    | Six semantic palettes/modes and shared action controls are current baseline. Historical split Review in handoffs is not the audit runtime. Do not reopen approved palettes or duplicate its UI library.                                                                                                                                           |
| **MEDIA-VISUAL-001** | Independent design/evidence chat, source `1d44`; no product implementation in this audit baseline | Media owns photographic density, full-width 4:3 gallery, contained on-demand preview/larger detail, photo ratios, attribution and workflows. Global audit owns only shared grammar proposals. Media will reproduce F01 and use the agreed safe-focus API if required. Existing asset-to-Identity-cover gallery toggle is unsupported: exclude it. |

## Explicit coordination

With direct operator authorization, the audit sent environment/fixture/access information and shared
ownership boundaries to the Media chat. Media chose its own project `florabase-media-review-1d44`,
source `1d44`, port **15280**, database `florabase_media_review`, and separate media/dependency volumes.
Its concept gallery already uses **15281**; audit gallery uses **15282**. Neither workstream modified
or stopped the other's resources. Media's own 35-asset dataset, additional cover relationships and
explicit nonbotanical calibration images are **not** silently attributed to this audit's v5 fixture.

Both Review origins use localhost. Development cookies are host-scoped, not port-scoped, so concurrent
sign-ins replaced the other session cookie. We serialized login-dependent captures. Invalid
acquisitions are excluded from primary coverage and recorded in the external raw history. No cookie
security change, credential weakening or production workaround was introduced.

A concurrent resource check showed ~240 MiB available RAM and full 2 GiB swap. Browser screenshot
commands timed out; a new tab recovered rendering. No foreign stack was stopped to free memory and
no heavy test/gate was launched. This is environmental context, not a measured product performance defect.

## Audit-owned runtime

- Source `/home/alessandro/.codex/worktrees/bc88/florabase`, docs branch
  `docs/release-visual-audit-001` (the workflow permits feat/fix/docs/ci, so suggested audit/ was not used).
- Isolated project **florabase-ui-audit-bc88**, URL **http://localhost:15279**, role Review,
  private network `florabase-ui-audit-bc88_internal`. New PostgreSQL/media/dependency volumes carry
  that exact project and source; backend/database have no published host ports.
- Standard Review resources remain owned by `c902`; host guard correctly refused takeover. They
  were not started, reset, removed, migrated, reseeded or rebound. DEV/UAT/Stable Preview/Sourcing/
  production, primary main and foreign worktrees were preserved.
- A local-only harness in `/tmp/florabase-ui-audit-bc88/environment.py` reuses the existing Environment
  workflow, with the exact audit project/port constants and `/dev/null` config. It did not edit
  production workflow files. V4 runtime fixture copy changes only the exact project/origin allowlist
  to this dedicated instance; all role/database/source/media/ledger checks remain. V5 runner and
  packaged fixtures are unchanged. This is documented audit setup, not a new supported multi-Review
  feature or evidence that stock `make feature-review-status` recognizes this project.
- Only this new instance was migrated/seeded. New audit-only synthetic owner; v4 baseline / 80 references
  - v5 **ready / 252 managed references**. Counts: 37 identities, 43 SeedLots,16 Sowings, 19 Plants, 7 groups,
    18 Locations,5 Harvests,4 inventories,12 Orders,10 Suppliers,27 scheduled activities,13 Events,
    17 assets (9 local/8 external),18 media links,14 sites,24 identities with ranges,25 profiles.
- Images are licensed species illustrations, not proof of the owned fictional specimen or cultivar.
  Geographic assertions/coordinates are explicitly synthetic. No occurrence evidence fabricated.
  Optional WFO snapshot is absent; no source downloaded or synthetic authority installed.
- First startup wait expired while pnpm installed dependencies (159s); services later became healthy.
  First seed attempt refused on frontend health **before data writes**. Seed succeeded once healthy.
  Logs and harness are external. No source tests or build were represented as canonical acceptance.

## Evidence retention

Raw JPEGs/DOM sidecars/logs are outside Git under
`/home/alessandro/.codex/visualizations/2026/10/26/01a178c9-0d81-73f2-96a2-42047619aba9/release-visual-audit-001`.
Tracked-candidate documentation holds a compact selected index, gallery, route/consumer manifests,
proposal HTML and text. No broad binary collection is included. Review runtime/data remain available;
no cleanup/reset is scheduled. Static gallery server is read-only, loopback only. Reconstruct its
`/evidence/` mapping from the README; never substitute another source/dataset without updating metadata.

When a later Media change merges, compare only Media and shared consumers touched by its actual diff.
When an approved WFO source becomes available, add the Taxonomy graph/fullscreen evidence separately.
Keep source SHA/fixture identity on each integration capture rather than recapturing unchanged pages.
