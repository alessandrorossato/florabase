# HARVEST-003 implementation handoff

## Worktree and product decision

Implementation is in `/home/alessandro/.codex/worktrees/fbb6/florabase`, branch
`feat/harvest-003-seedlot-conversion`. HEAD, feature base and cached origin/main are
`c35197139c722bb06bdd531a2621d8b4f60073f2`, the merged HARVEST-002 increment (#67).
The primary checkout remains clean on main. All feature files remain unstaged/uncommitted;
no additional worktree was created. The final canonical `make feature-verify` passed on this tree,
recording `FEATURE_VERIFICATION_PASSED`; no commit or delivery has been run yet.

The original product-decision gate was needed. The operator subsequently approved B, guarded
reversal; that decision is implemented and is no longer an unresolved domain question. The operator
accepted product/visual UAT. Independent review and focused matrix are complete with no production
defect found. HARVEST-003 is promoted to `verified` from UAT and focused evidence; the final canonical
gate is complete. One reviewed local commit is the remaining step.

## Domain and lineage

An explicit Create Seed lot action accepts only active, already tracked seed material. It creates
one physical collection-produced SeedLot, one immutable used_for_propagation disposition, one
HarvestSeedLotConversion and the stock adjustment in a single transaction. Repeated partial
conversions can make multiple packets; Harvest saves/tracking/dispositions/depletion never infer a lot.
Non-seed, untracked and depleted material cannot convert.

The one producer is exactly the Harvest's Plant or PlantGroup. Existing advisory serialization,
producer assignment and cycle validation apply. No Harvest/item/inventory node was added to lineage.
Source BotanicalIdentity defaults creation but can be explicitly selected and corrected separately.
Harvest occurrence copies its PartialDate precision or absence. Target Location is confirmed separately
from source storage. No acquisition date, supplier, provenance, source notes, Event, media or Sowing
is inferred, and producer lifecycle/quantity/Location is not changed.

Exact partial transfer requires a positive compatible exact amount smaller than stock and subtracts
it exactly. Exact use-all requires the same exact target and depletes stock. Approximate partial use
requires explicit compatible approximate remainder; a measured target does not derive precision for
that remainder. Unknown source stays unknown on partial use. Approximate/unknown use-all depletes stock
with explicitly measured or unknown target quantity. Decimal values remain strings at the API boundary.
SeedLot weight units are g/mg; kg source stock requires an explicit supported-unit measurement/correction,
without silent conversion. Ordinary safe correction never replays conversion accounting.

Converted source_kind/producer fields are protected; a Harvest with any retained conversion cannot
change source. Existing inventory guards retain item UUID and seed material kind. Safe descriptive,
identity, Location, date, viability and ordinary quantity corrections remain possible.

## REVERSAL

The typed conversion retains unique inventory/disposition/result relationships, target quantity,
source correction version, applied/reversed status, UTC creation and reversal time. Before/after stock
state and quantity come from its exact immutable disposition. There is no generic JSON audit payload
and no new OperationReceipt kind.

Undo restores only captured before quantity/state in one transaction, marks the conversion reversed,
and retains the resulting SeedLot as lifecycle reversed. Historical producer lineage, Harvest/items,
inventory, disposition, conversion and reversal evidence remain. Active holdings and active Location
usage exclude reversed lots; totals retain them and their Location. New propagation and ordinary
reactivation are blocked. Standalone HARVEST-002 dispositions gained no generic reversal.

Source current state/quantity must equal the recorded after-state and its correction version must
match. A correction followed by a matching value still blocks stale restoration. Later standalone
dispositions block; later applied conversions must resolve newest-first. Reversed later conversions
are retained resolved history. Location-only correction is safe and source Location is not restored.

The result must remain active with its conversion-time quantity and exact canonical origin. Descriptive
text, independently corrected identity and Location do not block. Applied operation receipts and
Sowings without both reversed lifecycle and the matching explicit reversed propagation receipt block.
Existing downstream-first propagation reversal resolves dependents; there is no recursive auto-undo
or deletion. A historical row without explicit resolution evidence fails closed.

Mutation lock order is lineage advisory lock → Harvest owner → inventory → conversion (Undo) →
result SeedLot, then existing producer/Location validation where applicable. Rows are refreshed after
locking. Stock-only writes use owner → inventory and never acquire the lineage advisory lock.
Undo does not lock dependent receipts, avoiding inversion with existing propagation reversal.
Read-only eligibility is advisory; mutation repeats every check under locks.

Twelve deterministic PostgreSQL race cases use actual lock-wait observation and transaction events,
without sleeps: competing partial conversions; conversion vs disposition/use-all/source correction/
Harvest source reassignment/real lineage mutation; duplicate use-all conversions; Undo vs source
disposition/second conversion/SeedLot use/duplicate Undo/source correction. The lineage contender tries
a real producer cycle and conflicts; competing use-all produces one lot and no overuse. Other cases
produce one coherent serialized result or a stable conflict, with no stale restoration.

UI Undo is secondary, explains retained Reversed history and captured stock restoration, loads safe/
blocked eligibility, disables confirmation when unavailable and retains server conflict explanations.
Creation and history cross-links are on demand; the SeedLot projection batches nullable conversion IDs
in one query, with no history lookup per directory row.

## Migration and generated contracts

`20261004_0032` follows `20261003_0031`. The focused cycle test preserves a pre-existing inventory
and collection-produced SeedLot across downgrade/re-upgrade and proves zero inferred conversion rows.
It exercises empty cycles and refuses populated history downgrade before destructive changes under
exclusive table locks. Restrictive FKs, unique disposition/result links, positive finite typed quantity,
immutable facts, origin and reversed-state coherence guards are installed.

OpenAPI was regenerated through `make api-generate`; `make api-check` passed without drift.
Reads are authenticated; mutations require owner, CSRF and exact Origin. HTTP regressions cover these
boundaries, linked history, duplicate reversal conflicts and retained result lifecycle.

## Focused verification

QUALITY commands used the documented current-source quality project, without starting DEV.
PostgreSQL ran in `florabase-harvest003-20261004`, a task-owned tmpfs integration project with the
current backend source bound into the tests service. No real DEV database/media state was used.

- Backend unit/regression: 129 passed across Harvest, inventory, conversion, SeedLot model/schema,
  lineage and CSV service files; ordinary SeedLot service/API 6 passed; Sowing service 4 passed.
  Independent review added unit coverage for conversion creation, source-origin defaults, exact
  use-all and kg rejection, reversal eligibility/restoration, history projection and API success/error
  mapping. Final full backend unit suite: 595 passed at the unchanged 90.00% coverage threshold.
- Focused PostgreSQL matrix: 160 passed across CSV API, conversion, conversion migration, inventory,
  inventory migration, SeedLot API, lineage API/integrity and propagation reversal. After final
  boundary/correction additions, 4 selected cases passed. Final conversion/migration rerun after
  SQL readability cleanup: 42 passed. Existing Alembic path_separator warnings remain unchanged.
- Frontend: 48 passed across Conversion, SeedLotScreen and SowingScreen; the added identity/Location
  selection and final eligibility-network-failure cases brought Conversion to 9 passing cases,
  covering 50 unique focused cases overall. The latter keeps confirmation disabled and displays
  the failure inside Undo rather than leaving Checking visible with an error behind the modal.
- Final canonical `make feature-verify` passed on October 5: 595 backend unit tests at 90.00%
  coverage, 368 frontend tests across 40 files, 500 PostgreSQL integration tests, API drift,
  feature/workflow checks, formatting, Ruff, zero-warning ESLint, strict mypy (254 source files),
  TypeScript, production backend/frontend builds and the disposable Alembic cycle
  `20261003_0031 -> 20261004_0032 -> 20261003_0031 -> 20261004_0032`. The per-worktree receipt
  records the verified working tree. The initial gate exposed missing unit coverage (88.78%); added
  independent cases restored the unchanged 90% threshold. The final gate also exposed that the
  migration-cycle verification helper read only annotated assignments although real Alembic files
  use ordinary assignments. The helper now handles both forms; all 37 workflow helper tests pass.
  Final `git diff --check` passed.

An initial reused disposable test DB contained reference fixtures from pre-cleanup race runs, which
caused four existing empty-database CSV assertions to fail. Fixture cleanup was corrected; the fresh
matrix passed. Initial new-test selector/type/lint failures were corrected without weakening existing
assertions, validation, timeouts or configuration.

## Feature Review implementation smoke

With explicit operator approval, the prior Review resources owned by worktree 8dfa were removed
through its owning workflow. Current `make feature-review-up` and `feature-review-status` report
fbb6 source, isolated Review DB/media/dependencies, revision 0032 and healthy services at
`http://localhost:15174`. Synthetic exact/approximate/unknown/non-seed/depleted fixtures and one
Review owner exist only in this isolated environment; no fixture/credential/screenshot is in the diff.
On October 5 the retained Review frontend/backend were found stopped. The already approved
`make feature-review-up` restarted them without removing state; all services are healthy again,
bound to fbb6 with database/code head 0032.

Completed actual browser checks:

- 1440×844: exact Plant stock, source/identity/Location/date defaults, partial packet creation,
  explicit different target Location, success cross-link, partial-date preservation and canonical
  Plant → SeedLot lineage. No source Event/media/Sowing inference was visible.
- 1024×844: keyboard Harvest backlink, second packet via exact use-all, read-only exact target,
  original collected amount retained, depleted remainder and two independently retained conversions.
- 390×844 after browser reconnection: older packet Undo displayed source-change/later-use reasons
  and disabled confirmation; Cancel restored focus to its originating Undo button. Newest packet
  Undo restored exactly 20 items, retained the lot as Reversed with Harvest links and Plant lineage,
  and removed Start sowing. Collected quantity remained 30 items and the older packet stayed applied.
- Mobile PlantGroup conversion created an exact 35 g packet from approximate 100 g stock with an
  explicitly entered approximate 65 g remainder. The resulting lineage points to the exact group.
  A separately measured exact 20 g packet from unknown group stock left source remainder unknown.
  Non-seed fruit and depleted seed directory rows exposed no Create Seed lot action.
- Mobile dialogs had no horizontal overflow (390 px viewport; 375 px document scroll width;
  dialog client/scroll widths equal). Native quantity controls also passed keyboard selection.
  Review screenshots are outside the repository. The final 1440×844 view retains both the applied
  and reversed conversions beside restored current stock; the viewport override was reset.

The earlier browser disconnect interrupted smoke temporarily; reconnection resolved it and all
representative A–L cases are now covered by actual browser checks across the requested three sizes.
This is implementation smoke; operator product/visual acceptance is separately recorded as accepted.

## Roadmap reconciliation

The new current-direction section supersedes historical sequencing while retaining useful 0.1.0
planning. Actual graph statuses for lineage audit, LOCATION-003, ATTACHMENT-005, HARVEST-001/002,
MAP-002, SEARCH-001, major UI work and PERF-001 are preserved. The forward sequence is HARVEST-003 →
Supplier imagery/Reference → productivity v2 → Orders/Purchases → daily-use biology → final UI review
→ performance re-check → public Docker distribution → repository presentation → technical hardening
→ 1.0.0. BOTANY-003 remains a parallel planned track under its approved WFO contract and incomplete
public TLS-chain blocker; no workaround/source reselection was added. RELEASE-001 remains the planned
historical hardening contract, without deletion, promotion or repurposing.

## Handoff boundary

All feature work remains unstaged and uncommitted. The independent review found no production defect;
the canonical gate is now pending. No primary checkout modifications, extra worktree, global search
expansion, generic conversion/stock framework, BOTANY changes, stage, commit, push, PR, delivery,
merge or feature-finish occurred.
