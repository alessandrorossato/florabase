# PREVIEW-001 independent review and delivery handoff

Operator UAT passed at delivery. The later ownership-retirement regression and correction are
documented below. At delivery, independent review found no production/workflow defect; a fresh isolated
Compose acceptance smoke passed, and `make feature-verify` passed on the reviewed source tree. PREVIEW-001
is verified. Reviewed commit, protected delivery and finish are authorized follow-up steps. Next product milestone: **Collection productivity v2**.
BOTANY-003 and historical RELEASE-001 planning remain unchanged.

## Source and environment boundaries

Implementation worktree: `/home/alessandro/.codex/worktrees/80b3/florabase`.
Branch: `feat/preview-001-uat`. Base/HEAD: `bd7904316445f41570aadb827d680c24ba082900`
(SUPPLIER-003, PR #70). Changes remain dirty/untracked in this worktree; primary stays clean on main.

| Environment    | Purpose / source                                                     | Project                    | URL                      |
| -------------- | -------------------------------------------------------------------- | -------------------------- | ------------------------ |
| DEV            | Developer data; primary checkout                                     | `florabase`                | `http://localhost:5173`  |
| UAT Preview    | Synthetic operator acceptance; current dirty feature worktree        | `florabase-uat-preview`    | `http://localhost:15174` |
| Feature Review | Existing engineering/manual-owner dirty-source alternative           | `florabase-feature-review` | `http://localhost:15174` |
| Stable Preview | Explicit Git ref, clean detached source; existing commands unchanged | `florabase-preview`        | `http://localhost:15173` |
| Production     | Real collection; production topology                                 | `florabase-prod`           | Configured HTTPS origin  |

UAT reuses `Environment`'s Feature Review build contexts, non-root source binds, volume initializer,
health checks and forward-only migration graph. `compose.uat.yaml` adds only explicit UAT runtime
identity. It does not duplicate the Compose stack or change Stable Preview's detached-ref behavior.
UAT deliberately has new independent resources, rather than silently repurposing the existing Review
owner/data. UAT and Feature Review are alternative consumers of port 15174; stop Review from its
owning source first, retaining all its volumes. UAT does not take over another worktree's resources.

Builds and source mounts select this worktree, including tracked edits, untracked feature source and
migration files. Backend reload and Vite expose subsequent source edits. Restart `up` after lockfile,
image or migration changes. No source archive/ref checkout substitutes committed main for dirty UAT.

## Operator commands and credentials

```bash
make uat-preview-up
make uat-preview-seed
make uat-preview-status
make uat-preview-stop
make uat-preview-up
make uat-preview-reset CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview
```

**UAT PREVIEW ONLY: username `preview`, password `preview`.** This is intentionally public local
synthetic fixture data. It is never a production credential recommendation.

Up starts/rebuilds, migrates forward and waits for health; it never seeds. Seed is explicit. Status
reports source branch/SHA/dirty state, launch SHA, service health, DB current/code head, URL,
project/network, all persistence names, fixture version/initialization and owner initialization.
Stopped status reports fixture/owner inspection as unavailable rather than guessing persisted state.
No browser badge was added; CLI/status identity and Preview-prefixed data identify this environment.

## Fixture version 1

A bounded coherent basil/lavender/aloe collection creates 31 manifest identities:

- Three BotanicalIdentities: Ocimum basilicum, Lavandula angustifolia, Aloe vera; Preview common names.
- Two synthetic Suppliers: a nursery with primary local imagery and a media-free seed exchange.
- Four Locations: Preview collection → indoor seed shelf / greenhouse bench / outdoor herb bed.
- One custom GeographicPlace below existing canonical Italy and one explicitly synthetic,
  coordinate-bearing ProvenanceSite. These are demonstration coordinates, not factual distribution.
- Three active SeedLots: exact 48 basil seeds, approximately 80 lavender seeds, unknown aloe stock;
  purchased / exchange / unknown sources, distinct Supplier and provenance cases.
- Two Sowings: active spring basil tray (12 sown, 8 germinated) and historical completed lavender trial.
- Two Plants: directly acquired nursery aloe and basil derived explicitly from the spring Sowing.
- One active six-plant basil group explicitly derived from the same Sowing.
- Two ordinary observation Events plus the owned Event for a historical basil seed Harvest/item.
  Harvest is recorded collection history, without implicitly starting inventory or converting seeds.
- One tiny generated 96×96 PNG leaf illustration uploaded through the existing MediaAsset service;
  one external reference asset with reserved `example.invalid` URLs, which intentionally cannot load.
- Four explicit links: local illustration shared by Supplier, SeedLot and derived Plant (all primary),
  plus external reference linked to the direct Plant. Records without media remain available.

No provider/geocoding/download is needed for seed. No copyrighted images, screenshots or binary
fixture files are stored in the repository. Existing domain/service/Pydantic invariants create
records, lineage, owned Harvest Event/items, uploads, links and primary selections. No new domain
field, schema revision, API contract or authentication endpoint exists.

## Seed identity and operator edits

The versioned `.uat-fixture.json` manifest and `.uat-identity.json` workflow marker live in UAT's
media volume, outside production domain models. The manifest records service-generated UUIDv7 IDs,
not mutable names. The media-volume process lock serializes seed/status across service commits.

Repeated seed validates the expected manifest identities, record existence and stored binary digest.
It creates no second owner, object, media asset or link, and preserves ordinary operator edits and
operator-only records. It does not reset corrected text, quantities or primary choices. Missing/deleted
baseline records, interrupted initial seed (`building`), or a fixture-version mismatch require the
explicit guarded reset. An unrecognized owner/populated baseline is never adopted or overwritten.
The initial domain writes share a transaction until the normal primary service commits; the marker
remains `building` across any partial failure so a retry cannot duplicate or guess fixture ownership.
Reset is the supported recovery from interrupted baseline creation.

## Persistence and reset

These UAT-only named volumes persist through normal stop/start:

- `florabase-uat-preview_postgres_data`
- `florabase-uat-preview_attachment_data`
- `florabase-uat-preview_frontend_node_modules`

Stop uses Compose down without volume deletion. Reset requires the exact token above. It validates
rendered configuration, source, actual container/network/mount identity and every individual Docker
volume's project/name/source labels before stopping writers. It removes only those three exact
validated volumes, recreates the healthy stack and explicitly seeds the owner and baseline. No
`down -v`, Docker prune, worktree removal, DEV cloning, or production backup/restore change exists.
A failed rebuild/seed reports failure; it is not atomic availability and can leave UAT stopped or
unseeded. Resolve the error and use up/seed, or guarded reset for a partial baseline.

## Credential and environment safety

Host guards check expected UAT project, linked feature ownership, rendered source contexts, loopback
frontend port, internal DB/backend, isolated volumes/network, actual Docker source labels and binds,
actual DB settings and backend UAT mode/origin/cookie settings. Reset rejects ambiguous resources
before stopping/deleting. Runtime seed additionally requires the guarded resource marker, UAT mode,
development loopback cookies, fixed UAT DB URL/user, and actual PostgreSQL database/user identity.
An exported variable alone cannot seed. Disposable smoke projects are restricted to a UUID-shaped
UAT smoke name and a temporary loopback port; normal operator configuration stays fixed at 15174.

The fixture helper is explicitly mounted by the workflow, absent from production images and normal
startup. Normal bootstrap still rejects passwords shorter than 12 characters. After all UAT guards,
the fixture owner is created through normal bootstrap and its hash is set with the existing Argon2
hasher to the deliberately public fixture password. Login uses the unchanged real API, password
verification, owner checks, sessions/cookies, Origin and CSRF rules. No bypass/default owner is added.
DEV, Stable Preview, quality/integration and production commands never mount or invoke this seed.

## Verification and operator UAT

Focused checks passed: 19 Stable Preview, 29 environment, 37 feature workflow, 9 UAT helper and
18 real PostgreSQL fixture tests; Ruff/formatting/strict workflow and fixture mypy, feature graph
(89 valid), shell syntax, help and whitespace. Full UUID-scoped Compose smoke passed, including
reset and owner/media rebuild. Independent review also reran the disposable smoke on
`florabase-uat-preview-smoke-901ac5363b53`; all 18 PostgreSQL fixture tests and end-to-end smoke
scenarios passed. Canonical `make feature-verify` passed with 600 backend tests, 375 frontend tests
across 41 files, API drift, PostgreSQL integration, production backend/frontend builds, migration-cycle,
whitespace and receipt checks. Detailed evidence is recorded in `docs/progress.md`. The smoke snapshots
operator projects and primary Git before/after, includes read-only DB data checksums for running
operator databases, and cleans only its proved-new UUID-scoped containers/network/volumes. It never
resets operator UAT.

Operator review at `http://localhost:15174`, using `preview / preview`:

Operator UAT passed. The Preview was healthy, explicitly seeded and running from this dirty 80b3 source;
DB current and code head were `20261005_0033`. Normal browser login succeeded. Login and seeded Seeds,
Suppliers, Sowings and Plants were inspected at 1440×844, 1024×844 and 390×844 with no horizontal
overflow; mobile Dashboard, Supplier Photos and keyboard activation of Supplier detail were also checked.
The former Feature Review was stopped from its owning 73d8 source to release port 15174; its three
persistent volumes remain intact.

1. Sign in and browse the non-empty Dashboard, BotanicalIdentities and collection directories.
2. Compare nursery imagery with the media-free exchange Supplier; inspect shared asset links/primaries.
3. Inspect exact/approximate/unknown SeedLots, active/historical Sowings, direct/derived Plants and group.
4. Follow the explicit SeedLot → Sowing → Plant/PlantGroup chain; inspect observations and Harvest.
5. Browse the Location hierarchy and explicitly synthetic geography/provenance.
6. In Photos/Media Library, inspect local/primary/shared/absent media and the reserved external URL
   failure/reference state. It intentionally requires no remote fetch for seed.
7. Edit a Supplier or add an ordinary record, stop/start UAT, and confirm persistence. Repeat seed and
   confirm the edit remains. Only reset when deliberately discarding UAT changes.
8. Check login and core directories at 1440×844, 1024×844 and 390×844, including keyboard navigation.

The operator approved the UAT result. Independent review confirms the adversarial coverage and smoke;
no additional tests were needed. Canonical verification passed. The single reviewed commit, protected
delivery and finish remain the authorized next steps.

## 2026-10-06 — ownership retirement regression discovered during SEARCH-002

Delivered PREVIEW-001 rejected cross-worktree adoption correctly but lacked a supported way to
retire retained ownership: stop preserved it, and reset immediately recreated it. Consecutive
feature worktrees therefore could not start persistent UAT. SEARCH-002 includes only the narrow
workflow correction needed to restore that transition, separate from global search behavior.

`make uat-preview-remove CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview` runs from the owning
linked checkout, including a delivered detached owner. It validates exact resource/source identity,
refuses foreign volume users/network endpoints, stops writers, rechecks resources and individually
removes only the three UAT volumes plus the proved UAT containers/internal network. It does not
recreate anything or change Git/source/other environments. The next active feature runs up, seed
and status for a fresh baseline. Wrong confirmation and non-owners refuse. See the canonical
[transition instructions](development-workflow.md#uat-preview-and-operator-acceptance), including
how an older owner invokes the corrected Makefile without changing that owner's source.

Regression evidence and the actual `80b3` → `9f48` transition are recorded in the
[SEARCH-002 handoff](search-002-handoff.md). The disposable real Compose smoke now also covers
old-owner remove → new linked source up → fresh owner/media/fixture IDs → successful login,
while asserting all operator environments and primary Git identity remain unchanged.
