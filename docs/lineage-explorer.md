# LINEAGE-003 — Material ancestry explorer

A first-class, read-only view of recorded **material** ancestry centred on one record:

```text
SeedLot → Sowing → Plant / PlantGroup → (Harvest conversion) → new SeedLot
                    PlantGroup → extracted Plant
```

It is not taxonomy (`#/taxonomy`) and not phylogeny. No schema, migration or material semantics
changed; the explorer reads the concrete edges established in [lineage integrity](lineage-integrity.md).

## Edges and evidence

Only the six persisted source columns are edges. Each edge is owned by the downstream record:

| Edge                                | Owning column                           | Shown evidence                                          |
| ----------------------------------- | --------------------------------------- | ------------------------------------------------------- |
| SeedLot → Sowing                    | `sowings.seed_lot_id`                   | "Source recorded on this sowing"                        |
| Sowing → Plant / PlantGroup         | `originating_sowing_id`                 | "Source recorded on this plant / plant group"           |
| PlantGroup → extracted Plant        | `plants.originating_plant_group_id`     | "Extraction recorded on this plant"                     |
| Plant / PlantGroup → produced lot   | `seed_lots.producer_plant(_group)_id`   | Harvest conversion (link, date, applied/reversed) or "Producer recorded on this seed lot" |

Harvests, Events, Locations, BotanicalIdentity, provenance, taxonomy and media never create edges.
Reversed and inactive records remain, with their exact lifecycle. Conversion reversal keeps the edge
and marks its evidence reversed.

**Honest roots.** The oldest recorded record states its own origin: purchased / gift / self-collected
("independently acquired; no earlier collection record"), unknown ("origin not recorded"), or a
collection-produced SeedLot without a recorded producer ("producer was not recorded"). Nothing is
inferred beyond it.

**Generations** start at 1 on the oldest recorded record and increase at each recorded seed
production step (a SeedLot after its producer). They are not genetic generations.

## API

Authenticated reads (`require_authenticated_actor`), concrete kinds `seed_lot | sowing | plant |
plant_group`; a UUID of another kind is 404.

- `GET /api/v1/lineage/{kind}/{id}?limit=25` → `AncestryResponse`: `focus`, `ancestors` (nearest
  first, the existing walker) and the first page of immediate `children`.
- `GET /api/v1/lineage/{kind}/{id}/children?offset&limit` → `AncestryChildren` (`limit` ≤ 100):
  groups, then Plants/Sowings by kind, then UUIDv7 order; `total` is exact.

Each `AncestryNode` carries the record summary, its own `origin` kind, optional
`harvest_conversion` evidence and `descendant_count` for progressive expansion. Query count is
independent of path length: walk + four per-type batches + one grouped count + one conversion
lookup, plus the child page and its total (9 statements for a 22-ancestor chain, asserted in
`test_five_generations_use_concrete_edges_and_batched_lineage_queries`). The single-owner collection
model applies; the endpoints expose only summaries of records already readable by that owner.

## UI

`#/lineage/{kind}/{id}` renders within the focus record's section (Seeds, Sowings or Plants); no
navigation entry is added. Every record Lineage tab has **Explore material ancestry**.

- Recorded origin: oldest-first vertical chain, relationship verbs, lifecycle chips, evidence and
  **Explore from here** (re-centre; browser Back returns).
- Recorded descendants: one 25-record page per level; each node with descendants has a native
  disclosure button (`aria-expanded`, `aria-controls`, named with its record). **Show N more** loads
  the next page and moves focus to its first record.
- Loading, not-found, error/retry and per-level error/retry states. Phone width narrows the branch
  indent and raises controls to touch height. Existing tokens (`--lineage`, `--lineage-subtle`) and
  primitives (PageHeader, InfoDisclosure, LifecycleStatus, DetailEmptyState) only.

## Synthetic review cases

`ensure_lineage_explorer` (Feature Review only, marker `lineage_explorer_extension=1`, 47 records)
builds through owning services: a purchased root packet; a branching Sowing with a Plant group, a
dead mother Plant, a transferred sibling and a reversed mistaken Plant; an extraction; a mother Plant
Harvest with two conversions (one reversed); a second-generation Sowing and Plant; a directly
recorded group producer; a produced lot without producer; a same-identity independent Plant; and a
27-Plant flat exercising paging.
