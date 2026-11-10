# Phenology observations (PHENOLOGY-001)

Roadmap theme 5, "Phenology". Operators record real phenological observations (bud break,
flowering, fruiting, leaf change, dormancy) on a Plant or PlantGroup and compare them year by year.
Only recorded observations are shown; Florabase never infers that an unrecorded stage did not occur.

## Architecture decision

| Option | Assessment |
| --- | --- |
| **A. Structured phenology fields on existing Event records** | **Chosen.** A controlled `phenophase` plus an approximate-date flag on the existing `observation`, `flowering` and `fruiting` kinds. Journal, History, photos, PartialDate, ordering, correction, deletion, Schedule retention and reversal/reintegration retention already apply to these kinds, so no rule is duplicated. Existing flowering/fruiting Events stay valid as "stage not recorded". |
| B. One new Event kind per stage (or a new `phenology` kind) | Rejected. Eleven new kinds (or one generic kind) would need the same Journal filter, History, retention (`RETAINABLE`, reintegration), search and import vocabulary changes again, and would split "flowering" across two kinds, so the Journal would show the same botanical meaning twice. |
| C. A separate phenology table / timeline | Rejected. Event semantics already support every required observation; a second table would be a competing event system with its own dates, deduplication and History branch. |

Limitations of the chosen design:

- Florabase stores what the operator recorded, nothing more. There is no state machine: any
  stage may be recorded in any order, repeatedly, and a missing stage means **no observation
  recorded**, never "did not happen".
- No correction trail: a phenology correction updates the Event in place like any ordinary
  flowering Event (`updated_at` advances). Only measurements keep an append-only trail
  ([measurements](measurements.md)); add one for phenology only when real use needs it.
- No author field: Florabase is single-owner (multi-user is SECURITY-003, deferred). The source of
  every observation is the operator's Journal entry; recalled or estimated dates are flagged with
  `date_is_approximate`.
- PlantGroup observations mean "observed in the group", with no member count or proportion.

## Domain contract

| Concern | Decision |
| --- | --- |
| Vocabulary | Controlled `phenophase`, tied to the Event kind (below). Arbitrary strings are refused by Pydantic and `ck_events_phenology`. |
| Subject | Exactly one Plant or PlantGroup, as for every Event. On a group it means the stage was seen in the group, not in every member. |
| Date | Occurrence PartialDate at any precision (year, month, day) or unknown. Precision is preserved and never widened to a day. An undated observation is kept and shown under **Date not recorded**. |
| Uncertainty | `date_is_approximate` marks an estimated or recalled date (shown as "about"). It requires a date. Stage uncertainty belongs in the notes. |
| Repetition | Any number of observations per stage per year, e.g. two flowering onsets in one year (remontant flowering) or several "flowering" checks in one season. Nothing is merged or deduplicated. |
| Current state | A phenology observation never changes lifecycle, Location, quantity or lineage. |
| Correction | `PUT /api/v1/events/{id}` updates the same Event. Changing the kind clears or must re-select the stage; a stage incompatible with the kind is refused. |
| Deletion | Ordinary Event deletion rules: photos and completed Schedule links block deletion. |
| Retention | Observation, flowering and fruiting are already retainable observations: they stay attached for dead, lost, transferred, reintegrated or reversed records, and records may still receive them. |
| Identity | Events reference the Plant/PlantGroup UUID, never a name. Name correction, accepted-name reconciliation or a duplicate-identity merge (TAXONOMY-001/002) changes only the displayed label. |
| Lineage | Phenology creates no lineage, provenance or propagation relationship. |

### Stages

| Event kind | `phenophase` | Label |
| --- | --- | --- |
| `observation` | `bud_break` | Bud break / new growth |
| `observation` | `leaf_color_change` | Leaf colour change |
| `observation` | `leaf_fall` | Leaf loss |
| `observation` | `dormancy_entry` | Entering dormancy |
| `observation` | `dormancy_exit` | Dormancy exit / renewed growth |
| `flowering` | `flowering_onset` | Flowering began |
| `flowering` | `flowering_ongoing` | In flower |
| `flowering` | `flowering_end` | Flowering ended |
| `fruiting` | `fruit_set` | Fruit set |
| `fruiting` | `fruit_ripening` | Fruit ripening |
| `fruiting` | `fruit_ripe` | Fruit ready for harvest |

A `flowering` or `fruiting` Event without a stage (every Event recorded before PHENOLOGY-001) is
shown as "Flowering, stage not recorded" / "Fruiting, stage not recorded". An `observation` without
a stage is an ordinary note and is not phenology.

### Storage and API

Two nullable columns on `events`: `phenophase` and `phenophase_date_is_approximate`.
`ck_events_phenology` makes them all-or-nothing, restricts each stage to its kind and forbids an
approximate flag without a date. `EventWrite` and `EventResponse` gain
`phenology: {phase, date_is_approximate} | null`. No route is added. The migration is
`20261110_0046`; downgrade
refuses while staged Events exist instead of discarding them.

## Journal, History and display

- Journal: phenology observations are the same Events, shown once, under the existing
  Observations filter, with the stage on the card. Global Journal search matches stage labels.
- History: the existing Event row gains `Stage: Flowering began` (plus "approximate date", same labels as the Journal) as
  context. No extra History source or row exists, so there is nothing to deduplicate.
- Plant and PlantGroup Journal tab: a **Phenology** section with a "Record phenology" action
  (stage-first entry form), a year-by-year comparison and links to each underlying Journal entry
  and its photos.
- Year by year: each year shows a 12-month strip. Day and month observations sit in their month;
  year-only observations are listed as "month not recorded" and never drawn in a month. Every stage
  recorded in any year but not this one reads **No … observation recorded**. Undated observations
  are grouped last. Earliest-in-year wording is "First recorded", never "first ever".
- No line chart is drawn over categorical stages.

## Compatibility

Measurements (`kind = measurement`) carry no stage and stages never carry a measurement; both
constraints are independent. Schedule completion still creates stage-less Events; a stage can be
added afterwards by editing the linked Event. CSV import/export does not include Events.
