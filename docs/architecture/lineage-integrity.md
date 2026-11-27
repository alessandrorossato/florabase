# Lineage integrity audit

Audit base: `320865b` (HARVEST-001), `fix/lineage-integrity-audit`. This is a corrective audit of the
implemented contracts, not a new roadmap capability. Feature IDs/statuses remain unchanged.

## Canonical model established before modification

The source of recorded biological/material descent is the concrete aggregate foreign keys:

```text
Plant / PlantGroup producer → collection-produced SeedLot → Sowing → Plant / PlantGroup
                                                                    PlantGroup → extracted Plant
```

The producer edge already exists in LINEAGE-002; it permits multiple generations. It describes one
known collection producer, not genetic parentage, a maternal/paternal pair, or a Harvest conversion.
The source SeedLot of a Sowing is required. A Plant has exactly one immediate origin: Sowing,
extraction PlantGroup, or direct origin. A PlantGroup has Sowing or direct origin. An extracted Plant
stores only its group link; its group's Sowing and SeedLot remain upstream ancestors, never copied
onto the Plant. UUIDs are scoped by concrete entity type throughout traversal.

Receipts capture an operation's original facts and before/expected-after state. They prove eligibility
for specific compensation; they do not supply missing ancestry. Events journal occurrences. Initial
movement/status Event creation may update current Location/lifecycle; ordinary journal correction or
deletion never replays those effects. Aggregate rows remain authoritative current state.

## Invariant matrix

“Mutable” means the existing public correction contract, not unrestricted SQL access. Restrictive
foreign keys preserve referenced records; acyclicity applies to all six concrete edge alternatives.

| Relation / operation                | Biological/material edge?                  | Operational history?                                 | Mutable?                                                                                                     | Survives reversal?                                                 | DB enforcement                                                                                                   | API representation                                                                | UI representation                                                   |
| ----------------------------------- | ------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Producer Plant/PlantGroup → SeedLot | Yes, recorded material producer            | Not a receipt                                        | Correctable/clearable; only collection-produced; new historical producers refused                            | Existing links retained; produced lot blocks producer compensation | Concrete RESTRICT FKs; exclusive producer/source-kind checks; acyclic write triggers                             | `producer_plant_id` / `producer_plant_group_id`, typed summaries                  | Producer links; recorded upstream path                              |
| SeedLot → Sowing                    | Yes                                        | Transition may own receipt                           | Source correctable except reversed Sowing; no accounting replay                                              | Yes, Sowing retained as reversed                                   | Required concrete RESTRICT FK; acyclic triggers                                                                  | `seed_lot_id`, `seed_lot`                                                         | Source SeedLot; propagation path                                    |
| Sowing → Plant                      | Yes                                        | Transition may own receipt                           | Correctable except reversed result; direct/Sowing origin may switch                                          | Yes, Plant retained as reversed                                    | RESTRICT FK; exclusive origin check; acyclic triggers                                                            | `originating_sowing_id`, `originating_sowing`                                     | Propagation origin; upstream path                                   |
| Sowing → PlantGroup                 | Yes                                        | Transition may own receipt                           | Correctable except reversed result                                                                           | Yes, group retained as reversed                                    | RESTRICT FK; exclusive origin check; acyclic triggers                                                            | Same originating-Sowing fields                                                    | Propagation origin; upstream path                                   |
| PlantGroup → extracted Plant        | Yes, immutable immediate extraction origin | Receipt and extraction Event prove execution         | Ordinary editing cannot detach/replace origin                                                                | Yes, including reintegrated Plant                                  | RESTRICT FK; exclusive origin; Event/result/source composite FK; acyclic triggers                                | `originating_plant_group_id`, summary; propagation summary retains exact group ID | Extracted from group; extraction stage with original group context  |
| Reintegration                       | No new edge                                | Compensates extraction                               | Applied once after eligibility/confirmation                                                                  | Original extraction edge, Event and receipt facts retained         | Typed receipt/FKs, immutable original facts, unique compensating Event receipt; source/result Event composite FK | Eligibility, original group, historical Plant and Event                           | Original Plant group; reintegrated historical extraction evidence   |
| Plant transfer                      | No                                         | Whole individual leaves held collection              | Active only; transfer journal facts correctable                                                              | No transfer undo implemented                                       | Target RESTRICT FK; typed immutable receipt; new receipt/Event correlation                                       | Transfer response, lifecycle, Event and receipt kind/status                       | Transferred; transfer/history                                       |
| PlantGroup transfer                 | No                                         | Whole managed group; quantity preserved              | Active only; no partial transfer                                                                             | No transfer undo implemented                                       | Same typed group/Event protections                                                                               | Group lifecycle/quantity, transfer Event                                          | Whole-group transfer; historical record                             |
| Propagation reversal (three kinds)  | No new/deleted edge                        | Snapshot compensation                                | One applied receipt, downstream-first                                                                        | Result persists as reversed; source restored                       | Original receipt facts immutable; typed snapshots/FKs; retained result FK                                        | Eligibility/reasons, receipt status, retained result                              | Reverse creation; reversed status in paths                          |
| Other receipt reversals             | Extraction only via reintegration          | Purpose-specific compensation                        | Snapshot/dependency guards                                                                                   | Extraction history retained                                        | Existing typed receipts/FKs and service row locks                                                                | Reintegration endpoint; no generic receipt CRUD                                   | Reintegration; no generic undo                                      |
| Harvest source                      | No biological edge                         | Historical production context                        | Correctable through Harvest; deletable aggregate                                                             | Not a reversible propagation operation                             | Plant XOR group RESTRICT FKs; deferred Harvest/Event aggregate coherence                                         | `plant_id` / `plant_group_id`, typed `source`, owned `event_id`                   | Source; Harvest history, separate from Lineage                      |
| Event target / resulting Plant      | No independent ancestry                    | Journal; operation result reference where applicable | Ordinary history editable/deletable; extraction/reintegration edit protected; receipt-owned deletion blocked | Retained for compensated extraction                                | Exact-target checks, RESTRICT FKs; extraction source composite FK                                                | Target/result, operation kind/status                                              | Events and operation history                                        |
| Location                            | No                                         | Movement can journal a destination                   | Assignment and hierarchy correctable                                                                         | Retained current/last assignment; no path event sourcing           | Scope and hierarchy service guards; concrete RESTRICT FKs                                                        | `location_id`, path; direct/inclusive usage                                       | Current/last Location, physical containment                         |
| ProvenanceSite / Geography          | No                                         | Geographic/material provenance                       | Direct provenance/reference corrections permitted                                                            | References retained; derived paths reflect corrections             | Concrete RESTRICT FKs; propagated/extracted origin checks prevent copied direct provenance                       | Direct provenance fields, geographic/site summaries                               | Origin/provenance; navigate biological ancestors for derived origin |
| BotanicalIdentity / native ranges   | No                                         | Taxonomic/reference knowledge                        | Identity and names correctable independently                                                                 | Stable identity UUID/reference retained                            | Required concrete identity FKs; exact profile/place associations                                                 | Own identity vs upstream identity summaries                                       | Botanical context; identity aggregation is not lineage              |
| MediaAsset / RecordMediaLink        | No                                         | Shared visual reference                              | Metadata/link operations; target identity immutable                                                          | Links/assets follow their own retention rules                      | Exact target FKs; asset/target uniqueness; immutable link identity                                               | Asset and exact target links; independent primaries/covers                        | Photos/Media; no lineage traversal                                  |

## Corrections and historical interpretation

Current contracts explicitly allow SeedLot producer corrections, Sowing source corrections, and
ordinary direct/Sowing-origin Plant/PlantGroup corrections. Botanical identity need not match any
ancestor. Corrections update current concrete links; they do not revise immutable receipt facts,
replay source quantities/lifecycle, or recreate Events. Consequently a _transitive displayed path_
reflects authorized upstream corrections, rather than a frozen copy of every ancestor at birth.
Extraction's immediate group link and reversed results' immediate source are protected by their
ordinary correction services. This audit does not invent a prohibition on all upstream corrections.

A stale receipt is expected after some legitimate corrections. Propagation inverse eligibility
compares exact source/result relationships and structural snapshots; reintegration checks exact
original extraction/group/Plant and later corrections. Mismatch blocks restoration. Tests explicitly
prove that changing a group's Sowing can change the extracted Plant's corrected upstream path while
leaving the original receipt intact and making automatic reintegration/reversal unavailable.

Reversed records historically existed and remain readable. Reintegration keeps each historical Plant
and both group-targeted extraction/reintegration Events, restores the recorded group state, and marks
only extraction receipt status reversed. Repeated compensation is rejected. Multiple extractions
must be reintegrated latest-first. Exact groups decrement (last member completes the group);
approximate/unknown groups retain their representation and restore exactly that representation.

The Sowing summary is a tracked descendant/material summary, not an active-holdings count:
transferred/dead/lost/discarded historical individuals remain represented. Reversed groups/results
and reintegrated individual records contribute no additional exact count; historical result arrays
retain their lifecycle. Approximate/unknown groups never become exact individuals. Extracted Plants
now expose their concrete immediate group, so the UI can place them after group results rather than
implying direct Sowing origin.

No collection hard-delete API exists for these lineage records. Direct SQL deletion of required
SeedLots, Sowings, source groups, extraction results and receipt-referenced records is rejected by
existing restrictive FKs. Receipt original facts are UPDATE-immutable in PostgreSQL; receipt CRUD
is not exposed. Trusted administrative SQL can still delete otherwise unreferenced receipts or alter
status; that is outside the application operation contract, not an ancestry source or supported undo.

## Defects and narrow corrections

1. **Correction paths could create cycles.** Before changes, the three new API regressions returned
   200 for Plant, PlantGroup and Sowing corrections closing a producer loop. Only SeedLot producer
   correction previously traversed ancestry. Reuse the existing typed walker for every mutable
   source correction; return the existing `lineage_cycle` conflict without partial writes.
2. **Concurrent/disallowed SQL graph writes lacked cycle enforcement.** Revision 0030 installs
   statement-level transaction advisory serialization and row-level cycle checks for only the four
   existing collection tables' lineage columns. Service creation/correction/structural entry points
   acquire the same lock before aggregate locks; lifecycle-only operation SQL and readers do not.
   Multi-generation cycles are genuinely possible because of the already-supported producer edge.
   No generic graph entity/framework or new biological relation is introduced.
3. **Receipt shape did not correlate concrete references.** New receipts now verify source/result
   or target/Event correspondence at insertion for all six kinds. Existing receipts are not
   backfilled/revalidated against corrected aggregates. Immutable original facts and detectable
   legitimate stale receipts retain their established meaning.
4. **Upstream path hid lifecycle and could show another record's path during navigation.** Render
   the supplied lifecycle and key asynchronous state by concrete subject, ignoring aborted results.
5. **Sowing path flattened extracted Plants into the immediate result stage.** The additive
   `PropagationPlantSummary.originating_plant_group_id` carries DB truth to both existing Sowing
   presentations. Direct results and extraction results occupy distinct stages; extraction nodes
   explicitly name their source group. No visual restyling is included.
6. **Locked reads and origin comparisons could retain stale ORM state.** Five real transaction interleavings reproduced
   a second extraction from an already-completed group, unsafe reintegration eligibility after
   group correction, and source usage exceeding the newly corrected remainder. Explicitly refresh
   locked source/group/Plant/receipt reads using `populate_existing`, following the existing
   propagation-reversal pattern. For both Plant and PlantGroup, a stale origin comparison also
   skipped the forward-source guard after a concurrent correction and Sowing reversal. Compare the
   persisted edge under graph serialization before source-first row locking. All five regressions
   now require the winning committed state, including rejection of a newly attached reversed source.

Revision `20261002_0030` follows `20261001_0029`. Upgrade locks the four lineage tables and refuses
preexisting cycles without repairing/deleting records. Downgrade removes only the new guards;
records, receipts, snapshots and relationships remain intact. Graph writes require the application's
READ COMMITTED isolation: a snapshot established before an advisory-lock wait at REPEATABLE READ
would miss a winning edge. The statement trigger fails closed for non-READ-COMMITTED graph writes.
Reads and source-independent updates are unaffected by this requirement.

## Concurrency and query findings

Existing row locks serialize extraction, transfer, compensation and structural correction. Existing
integration tests cover last-member concurrent extraction, duplicate reintegration and duplicate
reversal with one successful application and atomic rollback. New real PostgreSQL contention tests
observe an advisory-lock wait: two individually valid cross-producer assignments would jointly form
a cycle; the first commits, the second sees it and rejects the cycle. No speculative new locking is
added to Events, Harvest, media, Location or geography. Five additional committed interleavings
prove cached ORM objects cannot bypass locked quantity/lifecycle/snapshot or forward-source guards.

Ancestry uses one recursive CTE with typed path/cycle detection, then at most four per-type summary
batches, independent of path length. The five-generation regression reads 22 ancestors in five
statements. No ancestor-per-query or unbounded accidental recursive loop was found. Sowing
propagation reads source, groups and Plants in three domain statements. Existing inverse eligibility
checks perform per-child receipt/history lookups; they are bounded by actual dependencies and are
not the lineage-display query. This audit makes no speculative optimization there.

## Evidence and test matrix

| Requested cases                         | Executable evidence                                                                                                                                                                                                                                       |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A/B: Plant and PlantGroup propagation   | `test_siblings_same_identity_are_independent_and_retained_after_transfer`; existing propagation API tests                                                                                                                                                 |
| C/D: extraction and reintegration       | `test_extractions_reintegration_and_downstream_first_reversals_preserve_full_path` for exact/approximate/unknown quantities; two distinct extractions and last-member completion                                                                          |
| E: all supported transfers              | Direct Sowing Plant, extracted Plant and whole group transfer in sibling test; quantity, exact upstream paths and blockers asserted                                                                                                                       |
| F: retained propagation reversals       | Complete group/extraction compensation then group/Sowing reversal; existing Plant and seed-count/weight/unknown reversal matrix                                                                                                                           |
| G: siblings                             | Direct Plants plus extracted Plant and group with a separate same-identity root; no cross-link/count contamination                                                                                                                                        |
| H: long history                         | Five supported production/Sowing/group/extraction generations, 22 ancestors; completed structural operations rather than inferred genealogy                                                                                                               |
| I/J: same identity and Location         | Independent direct Plant retains empty ancestry; identity correction, movement/history correction/deletion and Location reparent preserve all paths                                                                                                       |
| K/L: shared media and Harvest           | One asset links Sowing, unrelated Plants and both Plant/group seed Harvests; Harvest source/material correction, deletion and unlink preserve paths; no SeedLot producer inferred                                                                         |
| Geography/provenance/native range       | Shared site/direct provenance, native-range addition and GeographicPlace reparent preserve paths                                                                                                                                                          |
| Cycle/self/cross-type                   | All six edge alternatives tested directly in SQL; all mutable correction API paths; typed validator self/cycle/corrupt persisted path tests; concrete wrong-type FKs                                                                                      |
| Receipt mismatch/unsafe repeat/deletion | All six new receipt correlation guards; later valid source correction leaves receipt facts unchanged and blocks inverse; repeat reintegration/reversal and required ancestor/result deletion                                                              |
| Concurrency/migration                   | Actual competing edge writes with observed lock wait; populated guard-only downgrade/reupgrade preserves receipts/paths; legacy cycle blocks upgrade; stale snapshot isolation rejected; preloaded extraction/reintegration/seed-source records refreshed |
| API/generated/UI                        | Correction conflict/rollback API tests; summary exact group field assertion; generated artifacts; frontend lifecycle, stale-navigation and extraction-stage regressions                                                                                   |

Existing ordinary Event mutation, operation-owned protection, legacy/missing snapshots, observation
confirmation, structural snapshot corrections, rollback injection, auth/CSRF, Harvest coherence and
shared-media integrity suites remain part of the complete canonical gate.

## Verification and handoff

Focused PostgreSQL and backend/frontend checks are recorded in the progress milestone. The final
canonical gate is `make feature-verify`: feature graph, workflow helpers, quality/full unit/frontend
suites, disposable PostgreSQL suite, API drift, production images, 0029 → 0030 → 0029 → 0030 migration
cycle and whitespace checks. Its exact completed result is recorded in the final handoff, not inferred
from focused tests. No thresholds, tests, constraints, runner configuration or timeouts are weakened.

No commit, staging, push, delivery, merge, feature-finish or operator database upgrade is authorized.
The audit leaves its reviewed source tree available for independent logical review.

The complete gate reached 550 passing backend unit tests (91.25% coverage), 339 frontend tests,
437 PostgreSQL tests, successful production builds and the migration cycle, then exposed a
verification-helper defect: its receipt path assumed `.git` was a directory. Resolve the actual
per-worktree Git directory for both receipt writing and reading. A real linked-worktree regression
reproduces the failure and verifies isolated receipt storage and content comparison after the fix.
The unchanged canonical gate is rerun on the final tree; no verification stage is skipped.

## Changed-file manifest

- Database guard migration: `backend/alembic/versions/20261002_0030_lineage_integrity.py`.
- Domain services: `backend/src/florabase/lineage/service.py`,
  `backend/src/florabase/seed_lots/service.py`, `backend/src/florabase/sowings/service.py`,
  `backend/src/florabase/plants/service.py`, `backend/src/florabase/propagation/service.py`.
- Additive API contract and generated artifacts: `backend/src/florabase/propagation/schemas.py`,
  `backend/openapi.json`, `frontend/src/api/schema.d.ts`.
- Backend regression coverage: `backend/tests/test_lineage.py`,
  `backend/tests/test_propagation.py`, `backend/tests/integration/test_lineage_api.py`,
  `backend/tests/integration/test_lineage_integrity.py`,
  `backend/tests/integration/test_lineage_integrity_migration.py`,
  `backend/tests/integration/test_database.py` (new expected migration head).
- Semantic UI and coverage: `frontend/src/lineage/LineagePanel.tsx`,
  `frontend/src/lineage/LineagePanel.test.tsx`, `frontend/src/sowings/SowingScreen.tsx`,
  `frontend/src/sowings/SowingScreen.test.tsx`.
- Documentation: `docs/lineage-integrity.md`, `docs/domain-model.md`,
  `docs/architecture.md`, `docs/progress.md`. The feature graph is unchanged.
- Gate support: `scripts/feature-tree-fingerprint.py`, `scripts/test-feature-workflow.py`.

## Deferred capabilities

LINEAGE-003 graphical navigation, branching genealogy, sexual/multiple parentage, new propagation
types, generic undo, transfer undo and Harvest → SeedLot conversion remain deferred. The current
Sowing API/UI exposes its direct source and propagation summary; the shared recursive lineage
service can walk Sowing ancestors, but there is no public Sowing `/lineage` route or full upstream
Sowing panel. Navigating the linked source SeedLot exposes older generations. A richer Sowing
upstream surface is future work, not silently implemented by this audit.
