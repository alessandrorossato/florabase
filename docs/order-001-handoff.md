# ORDER-001 implementation handoff

Operator UAT and independent review passed, including acceptance of the shared acquisition
reconciliation flow. The canonical feature gate passed on the final reviewed tree. This handoff records
implementation and verification evidence; protected delivery and local finish are pending.

## Worktree and scope

- Worktree: `/home/alessandro/.codex/worktrees/3558/florabase`.
- Branch: `feat/order-001-purchase-orders`, initialized with `make feature-init`.
- Resolved base `origin/main` and unchanged HEAD: `732d6b150156a2573bda84f453b05ed0fe8a7c33`
  (HISTORY-001 / PR #75).
- At the original visual handoff, 72 intentional paths were unstaged: Orders
  capability/migration/tests, additive SeedLot relationship,
  Search/Saved Views integration, approved navigation/eyebrows/vocabulary, generated API artifacts,
  versioned synthetic UAT fixture and documentation. No unrelated work was present initially.
- At the original implementation handoff, no feature gate, staging, commit, push, delivery, merge or
  finish had run. Primary checkout was not edited;
  only the explicitly authorized guarded retirement ran from the previous UAT owner's worktree.

## Domain and physical lots

An Order is one purchase transaction, independent of its reusable Supplier and physical SeedLots.
Fields are UUIDv7 ID, optional Supplier, `ordered_on` PartialDate, reference, exact total/currency,
notes and UTC timestamps. Null preserves unknown knowledge. Year, month and complete date are
retained without invented components. Order date never automatically supplies acquisition date; an explicit reviewed copy preserves its precision.

Price is the known total transaction amount, with non-negative zero permitted. API money is decimal
text, bounded to 24 integer/fraction digits, stored in unscaled Numeric and returned without floating
point, rounding or exponent notation. Total and three-uppercase-ASCII-letter currency must be set or
cleared together. No FX, cross-currency total, per-lot allocation or payment data exists. References
trim whitespace, allow Unicode, reject controls, cap at 255 and are non-unique. Notes cap at 20,000.

New Supplier assignments require an active Supplier; unchanged retired historical links remain
readable/editable. There is no Supplier deletion workflow. Supplier overview links to its exact
filtered Orders directory; material counts/recency are unchanged and no financial summary is added.

Each SeedLot has zero or one Order. Purchased/purchased-fruit retain their exact source; Unknown
proposes Purchased in the shared preview. Known incompatible sources require a valid explicit saved
correction first, with conversion/reversal protections intact. Known Suppliers must agree; blank lot
Supplier proposes filling, and a mismatch requires **Use Order supplier**. Clearing an unsaved Supplier
cannot hide stored knowledge or bypass confirmation. Unknown Order Supplier preserves known lot Supplier.
Order Supplier edit refuses contradictions with linked lots, without implicit synchronization.

SeedLot → Order, Order → existing SeedLot and Order → new SeedLot all use `orders.reconciliation`.
Selection previews without mutation. Existing Apply saves only confirmed acquisition fields/link;
other form drafts remain unsaved. Both Order and SeedLot versions are checked under lineage/lot/Order
locks; stale refusals mutate nothing. Refresh previews stored acquisition fields before another Apply.
Unlink on normal Save removes only the relationship, retaining confirmed source/Supplier/date values.

Acquisition is vertical: Source, Order search, read-only transaction context, Supplier, acquisition
date. Known Supplier defaults Order search to that Supplier, with explicit Show all for conflicts.
Origin stays separate. **Link existing seed lot** on Order detail uses bounded eligible search and
opens the same preview; Apply refreshes linked physical lots and navigation works in both directions.
The preview names and links the selected physical SeedLot so same-identity packets remain distinguishable.

Add seed lot prepares a server-resolved Order/known-Supplier/Purchased draft. Identity, quantity,
harvest date, Origin/provenance, Location and lineage are not inferred. Acquisition date is an optional
confirmed copy, unchecked by default; different receipt dates are preserved by default. Year/month/day
precision is exact. New-lot Apply changes only the draft; creation revalidates Order version and final
confirmed acquisition fields. Multiple packets stay independent records.

Order total/currency are read-only transaction context, never copied or divided as a SeedLot price.
No new migration, stored reconciliation history, OrderLine or allocation mechanism was added for UAT.

[Full domain and API contract](orders.md).

## API, directory, search and views

Authenticated routes are GET/POST `/api/v1/orders` and GET/PATCH/DELETE
`/api/v1/orders/{id}`, plus read-only purchase preview and eligible SeedLot choices, protected
purchase-context Apply and confirmed new-lot creation (see the full contract). Mutations require owner, exact Origin and session CSRF. PATCH validates the
complete merged state: omitted fields remain unchanged and explicit null clears knowledge. Typed
404/409/422 errors explain missing references, purchase/Supplier conflicts, in-use deletion and
invalid state. Deletion is 204 only when no SeedLot references the Order; no silent unlink/cascade.

Directory text searches direct reference, Supplier name and notes using literal case-insensitive
substring matching. `%`/`_` are literal. Exact Supplier filtering composes with search. List order is
known year/month/day descending, unknown components last, then UUID descending. The response owns
the authoritative total and bounded page (default 50, maximum 100; offset maximum 100000).
Detail linked lots are independently bounded, and counts include retained historical lots.

`#/orders` provides compact rows/counts, read-first details and native create/edit/confirm-delete
dialogs. Errors stay inside the owning dialog. Linked SeedLots and Supplier have exact detail links.
SeedLot detail adds explicit transaction context beside its independent acquisition/origin fields.

Orders Saved Views use v1 surface `orders`, keys `q`/`supplier_id`; opening restores the canonical
URL at page one. Transient selection, dialogs/forms and offsets are excluded. Global Search adds
`kind=order` under Sourcing beside Suppliers, searching only direct transaction metadata with exact
Order links. Linked botanical names never confer a match or duplicates. Collection-only structured
filters continue excluding Orders. Count/page query bounds remain two per kind, at most 30 SELECTs
for 14 kinds plus shared paths. Orders do not expand Activity History.

## Approved information architecture

| Macroarea / page eyebrow | Destinations                                               |
| ------------------------ | ---------------------------------------------------------- |
| Overview                 | Dashboard                                                  |
| Collection               | Seeds, Sowings, Plants, Harvests, Locations                |
| Activity                 | Journal, History                                           |
| Explore                  | Botanical identities, Media, Geography, Collection origins |
| Sourcing                 | Suppliers, Orders                                          |
| Tools                    | Import / Export, Labels                                    |

Places/Reference sidebar groups are removed; unknown old collapsed-state keys are ignored. Explore
and Sourcing reuse keyboard disclosures and active-route auto-expansion. Mobile More retains every
destination. Existing routes remain stable. Collection origins preserves `#/map`, internal
`provenance_map`, geographic/site contracts and directly associated material semantics. Permanent
copy describes where collection material is recorded as coming from; it implies neither botanical
range/distribution, seller address nor current Location. Record detail entity headings are retained.

## Migration and retention

`20261008_0036_purchase_orders.py` follows `20261007_0035`. It adds Orders with PartialDate and
finite money/currency constraints, restrictive Supplier FK, date/Supplier indexes, nullable indexed
SeedLot Order FK/source constraint and the `orders` SavedView surface. Old lots remain valid and
unlinked; there is no backfill or source/date/quantity/lifecycle conversion.

Downgrade locks Orders, SeedLots and Saved Views and refuses while any Order or Orders Saved View
exists. Tests separately prove both refusal cases retain data. Explicit removal permits safe empty
downgrade/re-upgrade and leaves pre-existing lots intact. No application-startup migration was added.

## Operator-UAT refinement evidence

- Shared contract: source compatibility/Unknown proposal, blank/matching/conflicting/unknown Order
  Supplier, exact optional date copy, draft-only prefill, confirmed creation, no material inference,
  independent multiple lots, retained unlink fields, conflicting Order edit and both stale versions.
- Final PostgreSQL run: **645 passed**, including **27 purchase-context tests** and the original
  **21 Order tests**, in a fresh disposable Compose project. Cleanup removed only its own resources.
- Final focused backend regressions: **52 passed**. Whole-backend Ruff/format and strict mypy
  (**292 source files**) pass; authoritative OpenAPI `--check` passes.
- Final frontend regressions: **50 passed across 4 files** (SeedLotScreen, OrderScreen, OrderPicker,
  PurchaseContext). Whole-frontend ESLint, strict TypeScript, Prettier and generated API drift checks pass.
- Backend and frontend production runtime images built successfully with
  `florabase-order-001-refinement-{backend,frontend}-check` tags; no deployment was operated.
- Feature graph: **93 valid**, ORDER-001 remains `implemented`; no refinement migration was added.
- Browser DOM/interaction/layout checks at **1440×844, 1024×844 and 390×844** confirm one vertical
  Acquisition flow, exact readonly transaction context, filtered Order choices and deliberate Show all,
  Supplier confirmation gating, optional date copy, Cancel/Escape without mutation, reverse selector
  search and Apply/refresh, explicit new-lot creation and unlink retaining Source/Supplier. The copied
  month-only date is `2026-09`, with no day input or inferred quantity/storage/origin/harvest date.
  Inspected views have no horizontal overflow; viewport override was reset. No screenshots were taken.

## Independent final verification

- Independent review found no Order/domain, reconciliation, migration, security or navigation behavior
  defect. The approved “Explore” and “Sourcing” navigation was correct; the pre-existing UX-001 test
  still expected “Reference.” Only that test assertion was updated to reflect the approved IA.
- `make feature-verify` passed on the reviewed tree: feature graph (**93 valid**), workflow guards,
  whole-repository Ruff/Prettier/lint/strict typing, backend unit tests (**787 passed**, **90.01%**
  coverage), frontend tests (**503 passed across 51 files**), API drift, PostgreSQL integration
  (**645 passed**), production backend/frontend image builds, migration cycle
  `0035 → 0036 → 0035 → 0036`, whitespace and verification receipt.
- ORDER-001 is `verified` in `docs/features.json`. The tree is still unstaged and uncommitted;
  protected delivery, merge and `make feature-finish` have not run.

Current logs: `/tmp/order-001-refinement-{integration,backend-tests,backend-build,frontend-build}.log`.
An interrupted earlier run had no retained completion output and is not counted. A mistaken nonexistent
backend test path and frontend mock/typing/lint issues were corrected without weakening checks; the
final successful runs are the evidence above. Canonical feature verification remains expressly deferred.

## Initial implementation evidence (before this UAT refinement)

- Backend focused tests: **178 passed**, covering Orders, SeedLot, Supplier, Search and Saved Views.
  `ruff check .`, formatting and strict mypy (**288 files**) pass.
- Real PostgreSQL: **618 passed**, including **21 Order integration tests** for exact Numeric/date
  constraints, FKs, purchase eligibility, Supplier conflicts, retention, auth/CSRF/Origin, Saved View
  CRUD, direct/literal search, deterministic paging/query bounds and populated downgrade safety.
  The first run's six schema/head expectation failures were corrected; the fresh complete run passed.
- Standalone migration cycle: previous main 0035 → head 0036 → 0035 → 0036 passed in disposable
  PostgreSQL using `scripts/verify-migration-cycle.sh`.
- Focused frontend regressions: **187 passed across 11 files**: Orders/selector, SeedLot, Supplier,
  complete App navigation, lazy/transition behavior, Global Search, Saved Views and Collection
  origins. The final 10 unaffected files contributed 182 passing tests; the corrected Supplier suite
  separately passed all five. SeedLot interaction tests preload their module to avoid testing cold
  compilation timing, and the Supplier photo test waits for its actual photo controls. Existing
  timeouts/assertions and the separate lazy-loading tests are unchanged.
- Whole frontend ESLint and strict TypeScript passed. Generated OpenAPI exporter `--check` and
  TypeScript generator `--check` passed; both generated artifacts are included.
- Production backend/frontend runtime image builds passed with task-specific
  `florabase-order-001-{backend,frontend}-check` tags. No running production services were operated.
- Changed UAT scripts pass the repository workflow-check Ruff/format rules and strict fixture mypy.
  `make test-uat-preview`: **19 passed**; real read-only fixture/guard tests: **19 passed**.
- Feature graph: **93 valid**; ORDER-001 acceptance/dependencies preserved and status `implemented`.
  Whole frontend Prettier and final `git diff --check` pass.

Integration logs: `/tmp/order-001-integration.log`; migration cycle:
`/tmp/order-001-migration-cycle.log`; production build logs:
`/tmp/order-001-backend-build.log`, `/tmp/order-001-frontend-build.log`. These are local ephemeral
implementation evidence, not a canonical verification receipt. No timeout/test policy was weakened.

## UAT Preview and browser checks

URL: **http://localhost:15174/#/orders**. UAT-only credentials: **preview / preview**.

Inspected prior ownership at `/home/alessandro/.codex/worktrees/ed24/florabase`, then retired it only
through its supported guarded `make uat-preview-remove
CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview`. Current worktree ran `make uat-preview-up`, explicit
seed, repeated seed and status. Backend/frontend/database are healthy; database head is 0036.
Fixture v2 has **34 baseline records**. Re-seeding retains existing edits and extra operator records;
incompatible/interrupted manifests still require guarded reset. DEV, Stable Preview, Feature Review
and production state were not operated. Disposable integration/migration cleanup used its helpers.

Synthetic baseline:

- Preview — Greenhouse Nursery → Preview — PO-2026-001, 2026-10-08, EUR 42.50 → two independent Basil
  packets; first has 48 seeds, second unknown quantity.
- Preview — Historical purchase, 2026-09, unknown Supplier/price; initially empty and now linked
  to the extra explicitly confirmed month-only acquisition example.
- Existing gift/exchange and unknown-source lots remain unlinked and unchanged.

Browser review additionally leaves one clearly synthetic long-reference USD Order with exact
`0.010000000000000001` and unknown date/Supplier, plus Saved View **Preview — Purchase review**.
These extras are outside the immutable fixture manifest and are not overwritten by seed.

Interaction/DOM/layout checks at **1440×844, 1024×844 and 390×844** cover Orders directory/detail and
create/edit dialogs, exact EUR/USD and PartialDate/unknown display, long reference wrapping, separate
lot links, Add seed lot prefill, Supplier navigation, Saved View create/open, sidebar/mobile reachability
and Collection origins vocabulary. No horizontal overflow in inspected Order/form/SeedLot/Supplier
views. A development reference-load interruption recovered via Retry. No screenshot files were taken.
The operator subsequently passed visual/product UAT; the accepted refinement examples follow.

Refinement examples were created explicitly through UI as extras outside the immutable v2 manifest.
Baseline records and operator edits remain preserved; no reset or re-seed was needed.

| UAT case                                           | Ready example                                                                                                                                                                                                                              |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Blank acquisition and Unknown Source               | **Preview — Reconcile blank acquisition**, unlinked, Source/Supplier/date unknown. Preview proposes Purchased and Supplier fill; Cancel leaves it blank.                                                                                   |
| Supplier match                                     | **Preview — Reconcile Supplier match**, purchased, Greenhouse Nursery, unknown receipt date, unlinked. Browser reverse Apply succeeded, then explicit unlink retained source/Supplier so either direction is ready again.                  |
| Supplier conflict and differing date               | **Preview — Reconcile Supplier conflict, acquired 2025**, purchased-fruit, Garden Seed Exchange, year-only 2025, unlinked. Show all Orders before selecting PO-2026-001; replacement requires confirmation and date stays 2025 by default. |
| Multiple independent physical lots and exact total | **Preview — PO-2026-001** retains the two separate Basil packets and EUR 42.50. Edit either packet's Acquisition to see read-only transaction information, with no lot price.                                                              |
| Explicit PartialDate copy on creation              | **Preview — Confirmed month-only acquisition copy**, Aloe identity chosen explicitly, linked to Historical purchase, acquired `2026-09`, unknown Supplier/quantity/Location/origin/harvest date.                                           |

Try the first three examples either in SeedLot Acquisition or Order detail → Link existing seed lot.
Selection never persists; review Source/Supplier/both dates and Apply explicitly. Creation from Order
starts with blank identity and receipt date; use the labelled date-copy review before Create if desired.

Operator scenarios:

1. Create/edit an Order with Supplier, year/month/day precision, reference, exact total/currency and
   notes; also check unknown fields and different currencies without an aggregate.
2. Add two normal SeedLots from one Order, selecting their own identity/quantity/origin/Location/date;
   verify both remain separate. Link from either direction through purchase preview; unlink in
   SeedLot edit and verify confirmed acquisition knowledge remains.
3. Attempt incompatible source/Supplier changes and conflicting Order Supplier edits; verify useful
   refusal and retained inputs. Linked deletion must stay blocked; review safe unreferenced deletion.
4. Follow SeedLot → Order → Supplier → filtered Orders. Check all source, provenance, acquisition and
   Location values remain independent.
5. Find an Order by reference/Supplier in Dashboard Global Search; open its exact detail. Save/open,
   rename/update/delete a filtered Orders view and confirm page-one state.
6. Inspect approved macroareas/eyebrows, keyboard collapse/active expansion, mobile More and
   Collection origins copy at all three widths. Existing routes/views must continue working.

## Roadmap and remaining owner boundary

EXPLORE-001 Species distribution and EXPLORE-002 Native ranges are
roadmap-only future candidates with separate semantics from Collection origins. The operator chooses
the next increment after acceptance. SCHEDULE-001 remains future Activity work; BOTANY-003 is
unchanged. No general ERP, OrderLine/SKU, Plant purchases, FX, invoice/payment secrets, History
expansion, range/distribution implementation or Schedule was added. No `.env`, real purchase data,
binary/build output, screenshots or secrets are included.

Operator UAT passed. This record tracks the independent review, canonical `make feature-verify`,
reviewed local commit and authorized delivery/finish.

READY_FOR_VISUAL_REVIEW
