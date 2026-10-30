# Journal: recording-first concept

**Design only.** No Journal table, API, migration, new attachment target or promotion service is
implemented by this study. Existing Events remain authoritative Plant/PlantGroup occurrences.

## Information hierarchy

1. Quick capture: large but bounded text composer, primary Save note intention, explicit subject/date.
2. Structured recording: clear launchers for delivered workflows, independent from text capture.
3. Recent notebook: secondary source-labelled entries, existing search/filter/Saved Views entry points.
4. Review queue: a later explicit note-to-fact review path, never automatic parsing and mutation.

A capture-first page should answer “What did you notice?” before showing a historical list. Keep
History nearby for retrieval and Schedule for intentions; avoid a tab that merges all three datasets.

## Conceptual wireframes

Square brackets below denote proposed controls, not working prototype features.

```text
DESKTOP · Journal                                  Search · Filters · Saved views
Record observations and collection work
┌ Quick capture ────────────────────────────────────────────────────────────┐
│ What did you notice?                                                     │
│ East bench feels cooler; basil may need a closer look.                   │
│                                                                         │
│ [Subject: collection / choose exact record…]  [When: unknown ▾]           │
│ [Category: Note ▾]  [Source: direct observation ▾]                        │
│ [Photos: link existing / upload*]                         [Save note*]    │
│ Capture time is separate. This text does not update a collection record. │
└─────────────────────────────────────────────────────────────────────────┘
Record structured work
[Harvest] [Sowing] [Germination → choose Sowing] [Move plants/groups]
[Plant/Group occurrence → choose target] [Complete scheduled work]

Recent notebook                               [All entries / search results]
Month-only observation · Basil group B · source Event → contextual Journal
Note · East bench · no occurrence date · source JournalEntry* → inspect
                                      * New data model required
```

```text
MOBILE · Journal
Quick capture
[Multiline note                         ]
[Subject: not selected                 ▾]
[When: unknown                         ▾]
[Category / source                     ▾]
[Photos*]                     [Save note*]
Record structured work [choose action ▾]
Recent notebook
  One text-first row; precision and source link
```

```text
LATER · Review note → structured fact
SOURCE NOTE (preserved)             PROPOSED STRUCTURED RECORD (editable)
Original text + declared precision  Choose canonical workflow and exact target
Original capture/source metadata   Enter/confirm actual occurrence precision
Photos linked to source            Resolve required fields; review consequences
                                   [Open canonical form] → [Confirm operation]
After success: source note ↔ explicit promotion receipt ↔ authoritative result
Failure/cancel: note stays; no partial botanical mutation or “promoted” flag
Correction: linked clarification/version; original content remains discoverable
```

## User journeys

### A. Observe a current Plant, with a photograph

Open Journal, enter an observation, explicitly choose the exact Plant (not merely its species),
choose day/month/year/unknown, review category and save. In an initial no-domain-change increment,
this opens the existing contextual Event editor with a draft; its target remains mandatory and
precision rules are unchanged. Photos use the resulting Event's existing Photos workflow after save.
Do not make a target primary photo or identity reference image look like an attached observation photo.
A single-screen atomic text-plus-upload save would require a separate transaction/retention design.

### B. Capture an uncertain, collection-level note

“Some trays looked dry last month” has no exact Sowing and no exact day. The proposed central notebook
allows no subject or an explicit collection scope, month precision only if the operator actually knows
it, and a source category such as direct observation or transcription. Save creates **only a note**.
Today this cannot be saved as an Event without choosing Plant/PlantGroup; show that limitation and
retain any draft rather than inventing an “unspecified Plant” or a dummy target.

### C. Record structured Harvest or germination

Choose the structured launcher before capture, or explicitly select “record structured work” after
reading a note. Harvest opens the real Harvest workflow and requires a real Plant/PlantGroup source;
germination opens the chosen Sowing's Germination tab. A Location-only note cannot silently become
a Harvest. The owning operation applies validation, effects and date rules. Do not copy its form into
a generic Journal save and do not create a second generic Event to summarize the same operation.

### D. Review a note later

Select an original note, choose a supported canonical operation, explicitly bind the exact target and
review extracted suggestions as untrusted drafts. Confirm actual occurrence date independently of
capture and planned due dates; missing precision stays missing. The canonical operation succeeds
before a durable promotion receipt is recorded. Record both links transactionally or use a reviewed,
idempotent reconciliation design if operation boundaries prevent one transaction. Retrying cannot
create duplicate facts. A failed/cancelled review leaves the note intact and eligible for later review.

### E. Correct an interpretation

Retain the original note's content and source metadata. Add a linked clarification/correction or
version that identifies what it supersedes. If a promoted fact is wrong, open its authoritative
correction workflow, then retain the exact correction/result link. A later clarification does not
replay Movement, Harvest, lifecycle or inventory effects. Permissions, deletion and attachment
retention must be approved before promising permanent original-source preservation.

### F. Close planned work

Complete from Schedule with the default **without Event**. History shows a terminal planning fact
using completed_at. For supported current Plant/PlantGroup kinds, the operator may explicitly record
an actual Event with its own date/notes. Water/Fertilize/Germination/Harvest have no generic Schedule
Event mapping; their canonical recording paths remain separate. Journal never infers an occurrence
from a task title, checkbox or overdue date.

## Persistence and API implications

Prefer an additive `JournalEntry` capability for unstructured source material over weakening the
Event exactly-one-target constraint. These are design questions, not a committed schema:

| Concern               | Proposed contract direction                                                                        | Risk / decision before implementation                                                                                                                                 |
| --------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity and content  | UUIDv7 entry, bounded normalized body, optional category                                           | Do not reinterpret existing Other/Observation Events as new notes without a migration decision                                                                        |
| Subject               | Initially zero or one exact typed reference, explicit collection scope when intended               | Decide supported types and whether multi-subject notes are ever required; free text labels do not become record IDs                                                   |
| Referential integrity | Narrow restrictive nullable FKs plus a count constraint for an agreed finite target set            | Additional targets affect permission checks, lifecycle eligibility, deletion guards, joins and serializers; avoid an unvalidated kind/id blob                         |
| Time                  | Nullable occurrence PartialDate plus immutable UTC recorded_at; updated_at remains correction time | Unknown occurrence must never default to today; clarify whether “when noticed” and “when transcribed” need separate fields                                            |
| Provenance            | Explicit capture source enum/description; authenticated author only if actually stored             | Source claims are operator assertions; do not label them verified facts                                                                                               |
| Correction            | Original content snapshot/revisions plus typed supersedes/correction links and expected version    | Review edit/delete policy, cycle prevention, access and export; source retention is a product policy, not a hidden audit-log promise                                  |
| Media                 | Reuse authenticated asset/link services with explicit JournalEntry FK/link ownership               | Review orphan cleanup, restrictive deletion, attribution, upload failure and retention; no new primary-photo or cover meaning by default                              |
| Promotion             | Typed result reference/receipt, reviewed mapping, idempotency and explicit correction lineage      | Define one note→many facts versus one-to-one; no automatic authoritative effects; existing Event update has no Schedule-style expected_version field to reuse blindly |
| Listing               | Authenticated server-side search/filter/page with stable order and truthful totals                 | Existing global Journal client filtering is not sufficient as a scalable new mixed feed                                                                               |
| API                   | Proposed create/read/list/update-or-correct plus separate explicit review/confirm contracts        | Agree v1 URLs, permissions, errors, concurrency and pagination first; regenerate OpenAPI and TS only in the later implementation                                      |
| Migration             | Additive tables/FKs/constraints; preserve all existing Event IDs, media links and History keys     | Decide mixed notebook presentation first; no bulk conversion/dedup by similar text, target or date                                                                    |

Extending Journal **beyond Plant/PlantGroup** is therefore not just adding picker options. A Sowing
annotation is not a germination count; a SeedLot note is not a stock correction; a Location note is not
a Movement; an identity note is not reference-source enrichment; a Harvest note is not a material
line/disposition. Each reference needs correct detail navigation, current/historical display,
authorization, referential retention and exact subject semantics. Whole-collection/no-target entries
need an honest scope label. Harvest/material subjects should be added only for an actual user journey.

## Phased implementation proposal

1. **Entry-point composition, existing contracts.** Operator approves recording-first hierarchy and a
   target-required Plant/PlantGroup composer that routes into the existing Event workflow. Keep recent
   notebook secondary; reuse canonical structured launchers. No promise of collection/unscoped save.
2. **Central source-note model.** Operator approves scope/target set, precision, authorship, correction
   and deletion/retention policies. Review migration and APIs, then implement independent storage,
   authenticated paging/search, concurrency and canonical error states with FULL verification.
3. **Media on notes.** Approve reuse/attachment ownership and failed-upload recovery; implement and
   verify protected thumbnails, attribution and retention. Initial Event photo journey stays available.
4. **Reviewed promotion.** First support one concrete operation. Approve result cardinality,
   original-source preservation, correction and idempotent receipt semantics before any implementation.
   No parser, assistant or template may bypass the explicit canonical confirmation step.

Templates are initially text prompts (“Condition”, “What changed?”, “Uncertainty/source”) and
categories aid retrieval; neither implies a structured botanical fact. New Event kinds, cross-domain
fact inference and automatic promotion remain outside the proposal's implementation phases.
