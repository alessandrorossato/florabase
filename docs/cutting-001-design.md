# CUTTING-001 vegetative propagation architecture

This decision originated in [PR #160](https://github.com/alessandrorossato/florabase/pull/160)
on 8 November 2026. The [original design at d4816e7](https://github.com/alessandrorossato/florabase/blob/d4816e791eea6609dc09955165983a0d88d5104d/docs/cutting-001-design.md)
preserves the proposed schemas, payloads, mockups and acceptance matrix. This recovery describes
the implementation merged in #167 at `95f5646e06bce98fdd3217ee5d6dfb52ea51a77d`.
The [feature register](features.json) at that commit records CUTTING-001 as `in_progress`.

## Decision and domain boundary

SeedLots represent seed inventory with storage, viability and count, weight or volume. Sowings
record dormancy treatments, germination and metrics such as time to germination. Cuttings are
perishable vegetative material that may be held before rooting, split across different setups or
rooted immediately. A rooting check captures callus, root initiation or loss. Combining these
records would distort seed inventory, germination analytics and seed order or harvest reconciliation.

The design selected a `VegetativeLot` for the acquired or severed batch, a `PropagationAttempt`
for each rooting setup and a `RootingObservation` for each check. The lot can exist before any
attempt. Several attempts can share its provenance while retaining independent setup and outcome.
Two resources require additional joins, constraints and UI, so atomic fast entry handles the
common take-and-root workflow without exposing a second save.

| Criterion | Separate lot and attempt, selected | Single typed vegetative propagation | Unified seed and vegetative tables | Harvest inventory plus direct specimen |
| --- | --- | --- | --- | --- |
| Stock and provenance | Hold and split one batch with one source record | Splits duplicate acquisition facts or require a second entity | Seed packet and clonal material semantics become conditional on kind | Collection harvests only, with no external or unknown intake |
| Migration and API | Additive tables and typed endpoints, with atomic fast entry | Smaller first schema, with a future split migration and API changes | Invasive FK and API rewrite across seed and sowing workflows | Minimal schema work, with manual orchestration across capabilities |
| Lineage and undo | First-class mother, batch, attempt and offspring edges and stock snapshots | Can link mother and offspring but loses the shared batch | Requires reworking existing traversal, constraints and receipts | Direct collection-produced origin has no mother FK or reversible rooting operation |
| Observations and integrations | Distinct rooting history, schedules and photos for held material and attempts | Observations fit, but held stock lacks its own target | Risks mixing germination, rooting and Journal concerns | A stock disposition cannot describe rooting progress or preserve a failed attempt |
| Future methods | Shared ownership model with method-specific extensions | Attached rooting and multi-source grafts strain a flattened record | Speculative polymorphism expands every existing contract | Cannot represent tracked attempts or multi-source lineage |

## Implemented ownership and invariants

- **Lot.** Stem, leaf and root cutting lots own botanical identity, source, acquisition or taking
  date, original count, remaining stock, location and notes. A collection-produced lot may have
  one mother Plant or PlantGroup and cannot carry direct external acquisition or provenance.
  The mother supplies a default botanical identity, which can be specified independently.
  Without a mother, an identity is required. Other sources cannot link a mother. Orders are
  limited to purchases and the service rejects conflicting order and lot suppliers. Source detail
  belongs to the Other source. Self-collected lots can contribute direct Collection Origins
  evidence. The mother edge provides inherited provenance without duplicating direct markers.
- **Attempt.** A lot can supply several attempts. Each attempt has its own PartialDate start
  and end, starting count, rooted count, location, setup and lifecycle. Known starting counts
  are positive. A recorded zero differs from an unknown count. An exact denominator bounds the
  rooted count and enables a rooting percentage. Failure allows zero or unknown rooted count and requires no
  unreversed established offspring.
  Completed and abandoned attempts remain readable, as do failures. Partial dates retain their
  original precision, and a definitely earlier end date is rejected.
- **Observation.** A rooting check owns its optional date and count independently of the
  attempt's current count. An exact starting count also bounds observation counts. History projects rooting observations, receipts and Schedule
  completions from their source records. Journal Events remain scoped to Plants and PlantGroups.
  Both cutting record types support photos, primary photos and location scopes. Schedule supports
  rooting checks for active cutting targets. Explore treats active cuttings as Current and
  terminal unreversed cuttings as Historical, with Living reserved for established specimens.
- **Stock.** Starting an attempt requires an active lot and locks it for adjustment. No adjustment
  preserves stock. Partial use subtracts exact counts, asks for an explicit approximate remainder,
  or preserves an unknown remainder. Use-all exhausts the lot, with exact stock reduced to exact
  zero and approximate or unknown stock keeping its representation. Lot and attempt edits use
  `expected_updated_at` to reject stale writes.

The [models](../backend/src/florabase/cuttings/model.py),
[schemas](../backend/src/florabase/cuttings/schemas.py) and
[services](../backend/src/florabase/cuttings/service.py) define the write invariants.

## Lineage and reversal

`Mother Plant or PlantGroup → VegetativeLot → PropagationAttempt → Plant or PlantGroup`
joins the existing genealogy. Offspring reference `originating_propagation_attempt_id` as
their exclusive origin. An external or unknown source ends the clonal path at the lot.
LINEAGE-003 traverses the clonal edges in both directions alongside sexual genealogy.
Application checks and PostgreSQL triggers share the lineage advisory lock. The recursive
`florabase_lineage_has_cycle` guard protects against mixed-generation cycles. See the
[lineage service](../backend/src/florabase/lineage/service.py) and
[reversal service](../backend/src/florabase/propagation/reversal.py).

Start and establishment issue `OperationReceipt` records with before/after state and structural
snapshots. Undo checks for structural drift and downstream dependencies before marking the result
and receipt reversed and restoring stored stock or attempt lifecycle. Undoing a start reverses
the attempt, leaving the lot readable even when fast entry created it in the same transaction.
Dependent offspring, media or scheduled work can block reversal. Rooting observations can remain
with explicit confirmation. A retained lot linked to a mother can block undoing the mother's
creation or extraction. Botanical identity merges repoint lots to the survivor, while receipts
retain their recorded snapshots for subsequent eligibility checks.

## Shipped workflows and deviations from the proposal

The [cuttings router](../backend/src/florabase/cuttings/api.py) defines the current API.

| Area | Shipped behavior |
| --- | --- |
| Fast entry | `POST /api/v1/propagation-attempts/fast-create` creates lot, attempt and start receipt atomically. An omitted start date inherits the taken date. An explicit null keeps it unknown. A standalone lot can later start an attempt via `POST /api/v1/vegetative-lots/{lot_id}/propagation-attempts`. |
| Edits and checks | Lot and attempt edits use versioned `PUT`, replacing the proposed `PATCH`. Observation create, correction and deletion are separate from changes to the attempt's rooted count. |
| Establishment | `POST /api/v1/propagation-attempts/{attempt_id}/plants` or `/plant-groups` takes flat result fields and inherits identity from the lot. An active attempt with a recorded zero cannot establish offspring. When the rooted count is known, exact establishments are bounded by that count. The resulting attempt may stay active, complete or be abandoned. Recording failure and updating the rooted count are separate edits. |
| Read and undo | Attempt detail includes the lot, observations and start receipt ID. Offspring use the separate `propagation-summary` endpoint. `GET` and `POST` on `/api/v1/cutting-operations/{receipt_id}/reversal` evaluate and execute undo. |
| Workspace | Cuttings has lot and attempt views, filters, saved views, preview and dedicated detail routes. The directory, Plant and PlantGroup details, Botanical Identity and Journal launcher lead into the creation form. Lot details can start an attempt. Attempt details handle rooting checks, establishment and undo. The original mockups remain design evidence for the proposed layout. |

## Migration and test strategy

[Revision 20261110_0047](../backend/alembic/versions/20261110_0047_cutting_propagation.py)
follows PHENOLOGY revision `20261110_0046`. It adds the three cutting tables and extends
specimen origin, receipts, lineage guards, locations, Schedule, media, primary photos and
saved views. Existing locations default to both cutting scopes off. Downgrade locks the
affected tables and refuses while cutting records, rooting-check schedules, Cuttings saved
views or enabled cutting location scopes exist.

The original strategy combined schema/service tests for source exclusivity, PartialDate,
uncertain counts and rates with PostgreSQL tests for atomic writes, constraints, concurrent stock
use, cycles, reversal and safe downgrade. It also called for History, Explore, Schedule, map and
media regressions and frontend workflow, responsive and accessibility checks. Existing evidence
can be traced to the [backend tests](../backend/tests/test_cuttings.py),
[PostgreSQL tests](../backend/tests/integration/test_cuttings_api.py) and
[frontend tests](../frontend/src/ui-pages/Cuttings/Cuttings.test.tsx). The PostgreSQL suite
covers exact-stock contention, mixed lineage and downstream-first undo, failed-attempt
representation, mapped provenance, purchase links, saved views, identity merge and downgrade
refusal. Those sources describe coverage independently of the checks run for this documentation
change.

## Deferred extensions

- Division and offsets/pups may reuse batch ownership and the lineage path. The proposed fast
  completion would atomically record separation and an already-rooted offspring.
- Layering would require an attached-to-mother phase, with the severance date distinct from
  rooting start. The proposed representation needs validation against that workflow.
- Grafting needs explicitly distinguished scion and rootstock provenance and cycle protection
  for both roles. The shipped attempt has one source lot and supports only `cutting`.
- The optional HarvestMaterialInventory bridge would follow the Harvest-to-SeedLot pattern
  with a typed conversion, a stock disposition, correction-version checks and reversible
  history. There is no harvest-to-cutting conversion in this increment.
- Dormant storage organs remain a separate TUBER-001 concern. Polymorphic seed and vegetative
  base tables and automatic mother Journal Events are outside this design. Existing CSV
  import/export does not restore propagation graphs.

See the [cuttings contract](cuttings.md) for operational behavior and the
[domain model](domain-model.md#vegetative-propagation) for the wider propagation context.
