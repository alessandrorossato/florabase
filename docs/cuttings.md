# Cuttings

CUTTING-001 uses Architecture 1 from the design in draft PR #160. A `VegetativeLot` owns
the material and source facts. A `PropagationAttempt` owns one rooting setup and its outcome.
A `RootingObservation` records a check of that setup. Stem, leaf and root cuttings use these
records. Seed inventory and germination retain their existing meanings.

## Quantities and outcome

The original lot count, current remainder, attempt starting count and rooted count are separate.
Uncounted material keeps a null quantity. An exact count may be used partially under a row lock.
An approximate partial remainder is supplied by the operator. Using all of an exact lot sets an
exact zero remainder and exhausts the lot. Using all of an approximate or unknown lot exhausts it
while preserving the quantity representation. The no-adjustment mode leaves inventory alone.
Fast creation saves both records and the operation receipt in one request transaction. The start
date defaults to the lot date and can be explicitly left unknown. When using all of an approximate
or uncounted lot, the operator can record a new count for the attempt.

Rooting rate is available for an exact starting count and a recorded rooted count. An active attempt
may report zero while rooting is still pending. A completed attempt can record full or partial
rooting, or an unrecorded count. Failed attempts remain in history, with either a recorded zero or
an unknown count. A rooting observation has its own optional PartialDate and count, independent of
the attempt's current rooted count.

## Lineage and reversal

A collection-produced lot may link one mother Plant or PlantGroup. External source references
belong to the lot. Establishment links a Plant or PlantGroup to its originating attempt, so the
ordinary upstream lineage path can continue from the lot through its mother. Writes use the
LINEAGE-002 advisory lock and database cycle guard. The resulting record's origin is protected from
ordinary editing. Corrections to a lot's source, location, lifecycle or remainder use the version
displayed by the editor. A stale edit is rejected.

Start and establishment operations issue typed receipts. Undo checks the receipt's structural
snapshots and downstream records. It restores the exact stored pre-operation stock or attempt
lifecycle. Reversed records remain readable. A rooting check can be retained with confirmation
when undoing a start. Linked media and scheduled work block cutting reversal. A retained vegetative
lot blocks undoing creation or extraction of its mother.

## Integration and delivery

Schedule supports rooting checks on active cutting targets. Shared photos and primary-photo
designation accept both record types. History projects operation receipts, rooting observations
and Schedule completions from their existing source records. Explore representation includes
active cuttings as current and terminal, unreversed cuttings as historical.

The existing CSV formats cover direct-entry specimens. They do not restore propagation graphs.
Database backup and restore preserve the cutting tables, receipts and lineage links.

Migration `20261110_0046` follows TAXONOMY-001 revision `20261109_0045`. When duplicate
identities merge, lots follow the survivor and the reconciliation ledger records their IDs.
Attempts get their identity through the lot. Existing receipts retain their original snapshots,
so a subsequent undo still checks the identity recorded at the time of the operation.

Before delivery, integrate both directions of clonal lineage into the merged LINEAGE-003
ancestry explorer and run canonical FULL verification on the frozen result.
