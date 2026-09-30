# Plants and Plant groups UX consistency

This is the Plants-specific refinement of UX-006 on `feat/plants-plantgroups-ux`, following the
accepted Shell, Seeds and Sowings pass. UX-006 remains `implemented`; independent visual acceptance
and the later delivery phase are separate from this handoff.

## Audit and decisions

| Surface                            | Finding                                                                                                                         | Refinement                                                                                                                                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Unified directory                  | Identity, type, origin, location, quantity and lifecycle competed as separate cells; sparse rows repeated unknown placeholders. | Compact identity and botanical context, lifecycle and tracking type, group-only quantity, and wrapping recorded context. An unlabelled record leads with its botanical identity.                                   |
| Desktop inspection                 | Preview promoted transfer or extraction ahead of normal inspection and lacked its collection photo.                             | Keep the established Quick Preview, with collection photo when designated, concise recorded facts, Open details as primary and Edit as secondary.                                                                  |
| Dedicated detail                   | Undifferentiated summary/origin sections repeated source labels; group quantity lacked an explanation of management semantics.  | Separate summary, managed group, origin/provenance, explicit extracted-Plant history and notes. Keep source links and botanical context. Historical records label location and quantity as retained facts.         |
| Ordinary versus structural actions | Transfer and extraction competed with Edit in the detail header.                                                                | Edit is the normal primary action. Collection operations are secondary actions in an explicit section. Reintegration and receipt-based reversal retain their existing explanations and guards below the record.    |
| Entry and correction               | Location was hidden with secondary fields; Cancel appeared above entry and there was a competing New action.                    | Identity, label, group-only quantity and location form Essentials. Origin/acquisition, partial dates, lifecycle and notes use Additional details; edit starts expanded. Final submit and Cancel follow all fields. |
| Keyboard flows                     | Type choice and edit did not consistently focus their task; cancelled structural dialogs did not restore their trigger.         | Focus the editor heading and restore creation, transfer and reintegration triggers when their task closes. Existing tab, picker and dialog keyboard behavior remains.                                              |

## Domain boundaries

- Plant means one individually tracked specimen and has no quantity. PlantGroup means multiple
  individuals of one BotanicalIdentity managed together. Counts remain exact, approximate or unknown;
  the directory spells estimates as `About N plants`. No percentages or inferred member totals exist.
- Extracted Plants are selected only by stored `originating_plant_group_id` from the already loaded
  collection, including inactive and reintegrated history. Shared identity, location or Sowing does
  not create a relationship. The list never subtracts members or establishes current membership.
- Exact extraction, completion of the last exact member, unchanged approximate/unknown quantity,
  whole-group transfer, immutable extraction origin, recorded receipt reintegration and bounded
  creation reversal keep the existing API and transaction contracts.
- Ordinary location editing corrects current state. Creating a movement Event records history and
  changes location. Editing/deleting history never replays current state. Events, Photos and Lineage
  stay on their existing lazy detail tabs and stable routes.
- Primary collection photos use the existing authenticated thumbnail component. External primary
  photos remain neutral until the existing Photos workflow opts into loading them. BotanicalIdentity
  covers are never substituted for a record's collection photo.
- No backend, API, migration, persistence, dependency, shell or shared-component contract changed.
  Styles are scoped to Plants; shared layout, preview, header, date and reference-picker components
  are reused without modifying their other consumers.

## Verification and rendered review

The live review used the production frontend and backend in a separate `florabase-ux-review`
Compose project, with disposable tmpfs database/media and fixture records. Operator data and the
existing development/performance projects were preserved. The review project was removed after
inspection, without volume-deletion commands.

| Viewport   | Rendered surfaces and evidence                                                                                                                                                                                                                       |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1440 × 844 | Populated directory, single-record filtering, Plant and PlantGroup Quick Preview, landscape/portrait primary photos, dedicated detail and extraction entry. Edit and Open details remain primary in their respective contexts.                       |
| 1024 × 844 | Plant detail/edit, location correction, movement Event, protected Photos tab, long botanical identity/location wrapping in directory and group Quick Preview.                                                                                        |
| 390 × 844  | Populated and one-record directories, sparse Plant creation, unknown-quantity group creation, group edit, long-text detail, bounded portrait photo, disclosure keyboard activation/value retention, transfer dialog and group Event/Lineage history. |
| 1024 × 600 | Populated scrolling directory/preview and receipt-based reintegration dialog. Native scroll surfaces remain available in the reduced height.                                                                                                         |

Read-only DOM measurements found no horizontal overflow in these reviewed views. The review also
covered no-match filtering, sparse optional fields, loading transitions, empty Event and Lineage
states, and local primary photos with landscape and portrait proportions. External-photo loading
privacy is covered behaviorally; no remote image was needed for visual review.

Live Plant workflow: create with only identity and an optional note, retain the note through
closing/reopening Additional details, edit a fixture Plant's current location, add a movement Event
and confirm its new location, inspect Event history and protected Photos. Live PlantGroup workflow:
create with unknown quantity, edit to approximate seven, edit to exact two, extract one individual,
reintegrate through the existing receipt, confirm the restored exact count and retained Reintegrated
Plant link, and inspect authoritative Extraction/Reintegration Events. Cancelling transfer restored
focus to its operation trigger. Missing optional data remained valid throughout.

Behavioral coverage includes both entry types, keyboard disclosure, retained hidden values and
submitted payloads, essential location, uncertain quantities, explicit extraction history, sparse
identity ordering, historical quantity/location labels, local/external preview photos, creation
focus restoration, transfer-dialog focus, and server-validation disclosure/error focus. Existing
tests continue to cover creation/edit failures, lifecycle/zero invariants, extraction, reintegration,
transfer, Events and session expiry. Exact final check results are recorded in `progress.md`.

## Scoped follow-ups

Suppliers and Reference workspaces should receive their own deeper row/detail/form consistency
passes. Their existing shared patterns were inspected as references; their product flows remain
outside this increment. Physical label review, global Event redesign, richer genealogy and any new
quantity or membership model remain separate work.
