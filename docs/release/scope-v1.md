# Florabase v1.0.0 release scope

This is the authoritative release contract for v1.0.0. It records what the operator approved,
what must be true before the release, what is optional, what is excluded, and how the scope can
change. Where another document disagrees with this one about v1.0.0 scope, this one applies.

Baseline: `main` at `947d77fc8bd2a757cdf49e28ec2e0f85b0374f1b`. A scope entry is not evidence that
work is implemented or verified. Three linked pages are part of this contract:

- [Task acceptance criteria](acceptance-v1.md): when each task named here is done.
- [Page inventory](page-inventory-v1.md): the pages gate G-UX evaluates.
- [Feature reconciliation](feature-reconciliation-v1.md): every `features.json` entry against
  this scope.

A feature's status and its release target are separate. Status stays in
[`features.json`](../features.json) and changes only on evidence; the release target says how an
entry relates to this release and is stored in the release-scope manifest
[`scope-v1.json`](scope-v1.json) (scope-change record, 2026-11-15).

## Operator-approved decisions

| # | Decision |
| --- | --- |
| 1 | **Release line.** The existing private beta (`v0.1.0-beta.N`) is followed by `v1.0.0-rc.N` and then `v1.0.0`. There is no intermediate public 0.1 stable release. |
| 2 | **No new domains.** No new roadmap domain is mandatory before 1.0. |
| 3 | **Installation.** Portable Docker Compose on linux/amd64 is the official installation. Building from source is for development only. The controller bundle is advanced and best-effort; it is not a separately certified installation path. *Amended 2026-11-21 ([ADR 0008](../decisions/0008-self-initializing-single-compose.md)): the official installation becomes the single self-initializing `compose.yaml`, and the controller bundle is withdrawn when INSTALL-001 is delivered.* |
| 4 | **Compatibility.** 1.0 supports documented database upgrades, paired database and media backups, and the documented CSV contracts. Compatibility of the HTTP API for outside clients is not guaranteed. |
| 5 | **Care entries.** Journal kinds for watering and feeding are wanted before 1.0. They are dropped from 1.0 if their implementation or migration risk threatens the release. |
| 6 | **Cuttings.** Cuttings is finished and certified, not hidden. |
| 7 | **Performance.** Thresholds are set from fresh measurements. No number is adopted before it is measured. |
| 8 | **Soak.** The first release candidate runs 14 days of real use. The period is extended if a meaningful incident or an unresolved risk appears. |

Further decisions made after the scope was established are in the
[scope-change record](#scope-change-record).

## What v1.0.0 is

A single-owner, self-hosted application for managing a personal botanical collection, installed
from published linux/amd64 images with the portable Compose file, behind an HTTPS reverse proxy
that the operator provides.

From 1.0.0 onward, within the 1.x series:

- A database created by any 1.x release can be upgraded forward by the documented procedure.
- A paired database and media backup made by the documented procedure can be restored by it.
- The documented CSV import and export columns keep their meaning.

## What v1.0.0 is not

- A stable public HTTP API. `/api/v1` is the application's own boundary and may change.
- Multi-user, offline-capable, or built for architectures other than linux/amd64.
- A certified source-build or controller-bundle deployment.
- A commitment to any theme listed as post-1.0 in the [product roadmap](../product-roadmap.md).

## Contracts this scope preserves

Release work must not weaken any of these. A change to one of them is a scope change.

- **Golden DEV.** The persistent Golden collection in primary DEV is initialized, replaced and
  verified only by the explicit operator actions in [Golden DEV operations](../dev-golden.md). It
  is never a test target.
- **Provenance.** Explicit lineage, source evidence and the separation of native range, observed
  occurrence and collection origin are kept. Nothing is inferred into a recorded fact.
- **Verification.** Exact-tree receipts, the fail-closed impact plan, protected `quality`,
  `integration` and `build` checks, and operator-only delivery remain as defined in the
  [development workflow](../development-workflow.md). Delivery never accepts reused stage evidence.
- **Data safety.** Application startup never migrates (narrowed by [ADR 0008](../decisions/0008-self-initializing-single-compose.md) on INSTALL-001 delivery: the backend process never migrates, and only the guarded `migrate` one-shot of `compose.yaml` does). No volume is deleted without exact
  identity proof. No shared-daemon prune is automated. Destructive actions keep their explicit
  confirmations.

## Scope classification

Every task has exactly one class. Acceptance criteria for each task are in the
[task acceptance criteria](acceptance-v1.md). A task identifier becomes a `features.json` entry
when its increment is selected.

### 1. Mandatory release blockers

v1.0.0 is not released until each of these is accepted.

| ID | Work |
| --- | --- |
| ENG-01 | Owner password change, and an offline reset command |
| ENG-05 | Disposition of the two TAXONOMY-001 concurrency findings: a two-session PostgreSQL regression, or an operator-approved documented risk disposition |
| ENG-07 | Performance re-measurement, operator thresholds and the supported-size statement |
| FN-01 | Finish and certify Cuttings (decision 6) |
| FN-05 | Preselect Today for new Journal entries (UX-DATE-001 decision D1, approved) |
| FN-06 | Verify the empty-database first run and fix what it shows |
| DOC-01 | One official installation guide for portable Compose; source-build and controller guides labelled per decision 3 |
| DOC-02 | Feature reconciliation and the release-scope manifest ([specification](release-target-schema-followup.md)) |
| DOC-03 | Correct the listed stale statements |
| DOC-04 | An end-user guide, proven by an unassisted trial |
| DOC-05 | Changelog, versioning policy and a vulnerability reporting channel |
| REL-01 | A release-candidate and stable channel in the release tooling |
| REL-02 | The real-host runs for G-INSTALL, G-UPGRADE and G-RESTORE |
| REL-03 | Release candidate, soak and release |

### 2. Required workflow enablers

These do not change the product. They are required because the mandatory work is delivered
through the development workflow, and they are not release gates in themselves.

| ID | Work |
| --- | --- |
| WF-01 | Stop idle Quality networks from consuming Docker address pools |
| WF-02 | Separate product-wide verification from workflow verification, without narrowing any product check |
| WF-03 | Own tests by directory and run the inventory check before the gate |
| WF-04 | A documented batch integration profile with provenance and retirement |
| WF-06 | A report-then-confirm command to retire resources of finished work |
| WF-07 | Human-readable WF-04 batch PR titles from a reviewed manifest summary |
| WF-09 | Exactly two tracked Compose files; workflow stacks derived from `compose.dev.yaml` at run time ([ADR 0008](../decisions/0008-self-initializing-single-compose.md)) |

### 3. Optional PRE-1.0 improvements

Wanted, not required. No mandatory gate depends on any of them. Each may be deferred by a
scope-change record, and a gate clause that mentions one states what applies when it is deferred.
The operator ruled explicitly on ENG-02, FN-02, FN-04 and DOC-06. ENG-03, ENG-04, ENG-06 and FN-07
are classed optional on the audit's recommendation and await an explicit ruling.

| ID | Work | Note |
| --- | --- | --- |
| ENG-02 | Baseline security headers in the bundled nginx | |
| ENG-03 | A test that every route requires authentication | |
| ENG-04 | Request identifier logging and an unhandled-error log | |
| ENG-06 | A real-browser smoke test on the production images | |
| FN-02 | Sorting in the Seeds, Sowings and Plants directories | |
| FN-03 | Watering and feeding Journal kinds | Decision 5: dropped if they threaten the release |
| FN-04 | Searchable pickers for large reference lists | |
| FN-07 | PWA installation verified on physical devices | Otherwise labelled experimental |
| DOC-06 | Documentation reorganisation and archive | |

### 4. Deferred to POST-1.0

- **WF-08**, removal of duplicated post-merge CI runs. Deferred: exact-main CI evidence and the
  release safeguards do not yet justify removing the duplicate jobs.
- **Product themes:** recurring care plans; plant health workflow; contextual entity timelines;
  QR quick capture; receiving and order lines; calendar export and reminders; user-provided
  phylogeny.
- **Feature entries:** BOTANY-003 and PHYLOGENY-001 (source-blocked), BOTANY-004, ENRICHMENT-002,
  EVENT-003, TUBER-001, WEATHER-001, REMINDER-001, ANALYSIS-001, TRANSFER-001, INTEGRATION-001,
  SECURITY-003, DASHBOARD-CUSTOMIZATION-001 and **GOLDEN-REFERENCE-001**.
- **Platform:** offline changes; arm64 images; an HTTP API compatibility promise; botanical
  matching beyond the read-only foundation.

None of these becomes a release dependency without a scope change. The themes stay described in
the [product roadmap](../product-roadmap.md).

### 5. Not release deliverables

| Class | Certification policy |
| --- | --- |
| **Internal foundation** | Delivered code with no user-facing surface. It is exempt from user-facing feature-completion certification. It is not exempt from regression and security verification: its tests run in the canonical gate, and any route or interface later added on top of it falls under the ordinary authentication and gate rules. BOTANICAL-MATCH-1A is the only entry in this class. |
| **Tooling** | Development workflow and test data. Its status does not gate the release. |
| **Historical record** | Audit or design records with no product deliverable. Closed without certification. |
| **Best-effort** | The controller bundle (decision 3). Kept and not certified. *Withdrawn on INSTALL-001 delivery ([ADR 0008](../decisions/0008-self-initializing-single-compose.md)).* |

## Release gates

Each gate is evaluated on one release-candidate commit and recorded under
`docs/release/evidence/` with the commit, host, dataset, command or procedure, result and the
operator's acceptance. A gate without a record is not met. No gate has a record at the baseline.

Every gate below is mandatory. Where a clause concerns an optional task, the clause says so and
says what applies when the task is deferred; a deferred optional task never fails a gate.

| Gate | Acceptance criterion | Verification method |
| --- | --- | --- |
| G-SCOPE | In the feature reconciliation regenerated for the candidate: every entry with target "PRE-1.0 certify" is `verified` or has a recorded exception approved by the operator; every "PRE-1.0 release work" entry is closed or has a recorded disposition; no entry with either target is `in_progress`. Entries classed internal foundation, tooling, historical record, best-effort or POST-1.0 do not count. | The reconciliation; `scripts/check-features.py` passes. |
| G-VERIFY | The candidate commit has a fresh full canonical receipt with no reused stages, and the protected checks are green on that commit. | `env -u REUSE FRESH=1 make verify-full`; `feature-tree-fingerprint.py verify`. |
| G-MIGRATE | An empty database reaches the candidate head. A database at the schema head of the last published beta, holding data, reaches the candidate head. The application refuses to start on any other revision. | Migration cycle; one recorded upgrade from the upgrade baseline below; `florabase.db.release_schema`. |
| G-INSTALL | On a host that has never held the source, the published assets are downloaded and verified, and the [installation guide](../installation.md) is followed without any step outside it, ending in a healthy stack, a bootstrapped owner, a sign-in, one created record and one uploaded photo. | Recorded run on one clean Linux host and on the operator's Synology host. |
| G-UPGRADE | From the upgrade baseline with data: paired backup, explicit schema upgrade, healthy stack. Then rollback by restoring the pre-upgrade pair with the previous images into fresh paths. Records and media digests match the source. | Recorded run on a real host. |
| G-RESTORE | A paired backup restored into an isolated project has the same Alembic revision, per-table row counts and attachment digests as the source, and the owner can sign in and open an original. | Recorded drill; `attachment_artifacts.py verify`. |
| G-SEC | (1) A recorded review of the candidate's routes lists every route that does not require authentication, and the list is exactly sign-in, health and readiness. *If optional ENG-03 is delivered, its test replaces the review.* (2) The image scan has no high or critical finding without a written disposition. (3) Only the frontend port is published. (4) The owner can change the password and recover from a lost one (ENG-01). (5) A vulnerability reporting channel is published (DOC-05). (6) *If optional ENG-02 is delivered, its headers are present; if it is deferred, the deferral is recorded and the installation guide's proxy example carries the headers.* | The review or test; the release workflow's scan; a port probe from a second host; `SECURITY.md`. |
| G-DATA | The Golden baseline verifies on the candidate images. A CSV export re-imported through the documented columns loses nothing. | `golden_dataset.py verify-baseline`; one round-trip check. |
| G-CORE | The core acceptance script below passes on the candidate images, starting from an empty database. No open critical or high functional defect. | Recorded operator pass. *If optional ENG-06 is delivered, its test covers the steps it automates.* |
| G-UX | For every entry of the frozen [page inventory](page-inventory-v1.md): no horizontal scroll at 390, 1024 and 1440 px; every control is operable by keyboard with visible focus; dialogs trap and return focus; the shipped themes meet 4.5:1 text contrast; the page is usable at 200 % zoom. | Recorded matrix naming the inventory version and the candidate commit. |
| G-DIAG | The installation guide's troubleshooting covers a wrong origin, a schema revision mismatch, an unhealthy container, bind-mount permissions and a lost password, and each case was reproduced once and resolved using only the guide. *If optional ENG-04 is delivered, every server error is logged with an identifier that the interface shows; if it is deferred, this clause does not apply.* | Documentation review and the reproduction record. |
| G-PERF | The measurement protocol in [PERF-001](../performance/PERF-001.md) is re-run on the candidate images with the Golden COMPREHENSIVE dataset. The operator sets thresholds and the supported collection size from those results, and the candidate meets them. | Published measurements and the operator's recorded thresholds. Until then no threshold exists (decision 7). |
| G-DOCS | The README, installation, upgrade, backup and restore, troubleshooting, user guide, changelog, versioning policy and data-source notes exist, match the candidate, and were the only instructions used in G-INSTALL, G-UPGRADE and G-RESTORE. | Those runs; a link check. |
| G-DIST | The tag, images, Compose asset and release manifest identify the same commit; attestations verify; every version surface agrees. | The protected release workflow and its checks, applied to the release-candidate channel. |
| G-SOAK | The operator's real collection runs on a release candidate for 14 days with no data-loss incident and every incident triaged. A meaningful incident or unresolved risk extends the period (decision 8). | The operator's log. |

### Upgrade baseline

The upgrade baseline for G-MIGRATE and G-UPGRADE is the last beta that is published when the
release candidate is cut. At the scope baseline that is **`v0.1.0-beta.5`** (commit `4c845b1`),
whose Alembic head is `20261013_0042`; `main` was then at `20261110_0047`. If a later beta is
published before the candidate, it becomes the baseline and the gate record names it.
`v0.1.0-beta.6` (commit `3552b3d`, Alembic head `20261110_0047`) was published on 2026-11-21
([publication record](evidence/beta-6-publication.md)). `v0.1.0-beta.7` (commit `1126c03`, Alembic
head `20261110_0047`) followed the same day and is the current baseline under this rule
([publication record](evidence/beta-7-publication.md)).

### Core acceptance script (G-CORE)

No step depends on an optional task.

1. Empty database: sign in, see a usable empty Today, follow the path to a first record.
2. Botanical identity, profile and a manual native range.
3. Supplier, order and a seed lot with partial and unknown values.
4. Sowing, germination observation, plant and plant group, extraction and a supported reversal.
5. Journal entry: a new entry opens with Today selected; record one with Today, one with
   Another date and one with Date unknown; photo upload; primary photo.
6. Bulk move; label print preview and QR lookup.
7. Schedule an activity, complete it, and see Today reflect it.
8. Harvest, stored material and a new seed lot; the lineage view shows the chain.
9. Search, filters and a Saved View; CSV export and import preview.
10. Session expiry during an edit and a server stop during a save: an error is shown and nothing is lost.
11. Change the password and sign in with the new one.
12. Cuttings: a material lot through rooting to an established plant, including a failed and a still-unknown attempt (decision 6).

## Certification of delivered features

Thirty-eight entries are on `main`, in scope and not `verified` ("PRE-1.0 certify" in the
reconciliation). ENG-01 and BRAND-01 were delivered after the reconciliation and are classed
`certify` by scope-change records, so the manifest has forty. None of them is certified by this
scope. The strategy is:

1. **One entry at a time.** Each entry is certified against its own acceptance criteria. There
   is no blanket promotion.
2. **Evidence mapping first.** For each entry, a row per acceptance criterion names the evidence:
   a test in the tree that the canonical gate runs, a step of the G-CORE record, an entry of the
   G-UX record, or a new focused check. A gate record counts for a criterion only when the row
   states which part of the record exercises it.
3. **On the candidate.** The evidence must hold for the release-candidate commit. Evidence
   recorded for an earlier tree counts only if the row states why it still applies.
4. **Recorded gaps.** A criterion with no evidence keeps the entry at its current status, and
   G-SCOPE then requires either the missing evidence or an operator-approved exception.
5. **Owner.** The mapping is delivered as a documentation change under `docs/release/evidence/`
   and reviewed independently before any status changes.

Entries with an active writer, Cuttings in particular, are certified by that writer's own
handoff and are not edited from outside it.

A criterion that later operator-approved work made untrue as written is certified against the
wording in the [acceptance-criterion restatements](restatements-v1.md). Only a confirmed row
applies. A proposed row leaves the original wording in force until a scope-change record
confirms it. The per-entry mappings are under
[`evidence/certify/`](evidence/certify/README.md), and the gate records use the
[G-UX](evidence/g-ux-template.md) and [G-CORE](evidence/g-core-template.md) templates.

## Legacy version references

These entries and documents were written for the beta or for a 0.1.0 release. Their text is
history and is not rewritten to say 1.0. This table is how the scope tracks them.

| Where | Reference | Treatment |
| --- | --- | --- |
| `features.json` RELEASE-001 | "first distributable Florabase 0.1.0 release"; "application version 0.1.0" | Text unchanged. Superseded for 1.0 by the gates above (decision 1). The entry is re-scoped or closed with the release-target schema. |
| `features.json` BETA-IMAGE-001 | "release for v0.1.0-beta.1" | Text unchanged. A genuine beta milestone; images are published through beta.5. Its pipeline feeds G-DIST. |
| `features.json` BETA-ACCEPTANCE-001 | "Accept v0.1.0-beta.1"; "a proposed seven-day … soak" | Text unchanged. It governs admission of the private beta only. Its seven-day proposal does not satisfy and does not shorten G-SOAK, which is 14 days on a release candidate (decision 8). |
| `docs/beta-foundation-001.md` | Beta acceptance contract, including the seven-day soak proposal | Unchanged and retained as the beta contract. Not part of the 1.0 gates. |
| `docs/release/history/product-roadmap-2026-11-11.md` | PRE-0.1 freeze path and v0.1.0 gates | Archived unchanged. |
| `docs/portable-installation.md`, `docs/installation.md` | `v0.1.0-beta.6` | Corrected at publication under DOC-03. |

## UX-DATE-001 decision D1

**Decided: a new Journal entry opens with Today selected.**

The question was whether Today is preselected in the Journal composer or the user must choose.
The alternatives were (a) nothing selected, with saving refused until a choice is made, and
(b) Today preselected. The design handoff recommended (a), and the code delivered in #177
implements (a) as the default of the `newEntryDateChoice` prop in
`frontend/src/events/OccurrenceDateChoice.tsx`. The operator approved (b).

The interface is not changed by this documentation. The change is task FN-05, assigned to the
functional batch, with these requirements:

- A new Journal entry defaults to Today.
- The user can explicitly choose Another date or Date unknown.
- Editing an existing entry keeps its stored date and that date's meaning.
- No date changes silently during editing, navigation or draft restoration.
- Focused regression tests cover the default and both alternatives.

## Changing this scope

1. A change is proposed as a record appended to the table below: the date, the affected
   identifier, whether it is added, removed, re-classed or re-targeted, the reason, and what it
   costs or saves.
2. Only the operator approves a record. An agent may propose one and must not act on it first.
3. An approved record is delivered as a documentation change to this file.
4. Work that is not in this file and not covered by an approved record is post-1.0.
5. Deferring an optional improvement needs a record and nothing else.

### Scope-change record

| Date | Identifier | Change | Reason | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-13 | — | Scope established with decisions 1–8 | Operator approval of the pre-1.0 audit direction | Operator |
| 2026-11-13 | ENG-02, FN-02, FN-04, DOC-06 | Classed optional; explicit deferral permitted | Should-do, not release blockers | Operator |
| 2026-11-13 | WF-08 | Deferred to POST-1.0 | Exact-main CI evidence and release safeguards do not justify removing duplicate jobs yet | Operator |
| 2026-11-13 | BOTANICAL-MATCH-1A | Classed internal foundation | No user-facing surface; regression and security verification retained | Operator |
| 2026-11-13 | FN-05 / UX-DATE-001 D1 | Decided: Today preselected for new Journal entries; implementation assigned to the functional batch | Operator decision | Operator |
| 2026-11-15 | DOC-02 | Decided: release targets are stored in the versioned manifest `docs/release/scope-v1.json` with the eight reconciliation classes; feature status stays only in `features.json`. No classification changes | Operator decision DOC-02 option B; closes the open point of the schema follow-up | Operator |
| 2026-11-15 | ENG-01, RELEASE-SCOPE-001, DOC-01, DOC-03, DOC-05 | Classes for the manifest: ENG-01 is `certify`; RELEASE-SCOPE-001, DOC-01, DOC-03 and DOC-05 are `release-work`, each from when it is in `features.json`. No status changes | ENG-01 is an implemented, user-facing feature on `main` whose certification must verify its criteria and evidence, including the applicable G-CORE check | Operator |
| 2026-11-15 | DOC-02 | Sequencing: the checker's release-candidate rule (`--release-candidate`) is delivered with the manifest in step 2; wiring it into the release rehearsal stays step 3 with REL-01. No classification changes | Operator approval, on condition that the flag is opt-in, leaves ordinary verification unchanged and is not wired into release tooling | Operator |
| 2026-11-15 | BRAND-01 | Added to the scope with class `certify`. No status change | Delivered in #186 without a scope record; user-facing artwork that ships in 1.0 and is certified against its own criteria | Operator |
| 2026-11-16 | UI-SYSTEM-001 | Restatement R24 of criterion 4 ([restatements](restatements-v1.md#confirmed-supersessions)): Today shows up to four distinct randomly selected Plant records, with truthful image attribution and responsive layout. The eight-photo grid is not restored. No status change; the other criteria are not waived, and selection, Plant links, image fallback and responsive presentation are still to be verified on the candidate | Consistent with the approved Today A — Operational design (2026-11-12), delivered in #177 | Operator |
| 2026-11-16 | CERT-01, CERT-02, CERT-03, CERT-04 | Registered with class `tooling` as the Batch 03 source identifiers: certification documentation (CERT-01), frontend certification regressions (CERT-02), Harvest certification regressions (CERT-03) and the scaffold verification gate (CERT-04). No new mandatory requirement, no reclassification of existing entries, no status change of any certification item | Each WF-04 source needs a feature identifier; these add evidence and checks and do not change the product | Operator |
| 2026-11-17 | WF-07 | Registered as a required workflow enabler: human-readable WF-04 batch PR titles from a reviewed manifest summary. No `features.json` entry, like WF-01 to WF-06; delivered by source WF-07 in Batch 04. No status or class change | Batch PR titles listing commit hashes are unreadable for review; the change affects the workflow only | Operator |
| 2026-11-17 | CERT-05 | Registered with class `tooling` as the Batch 04 source identifier for release-evidence reconciliation of BETA-IMAGE-001 and beta-postgres-repro-001. No status change of any other entry; supersessions and status moves it recommends need separate operator acceptance | Each WF-04 source needs a feature identifier; the record adds evidence and does not change the product | Operator |
| 2026-11-21 | INSTALL-001 | Added with class `release-work` and status `planned`: one self-initializing production `compose.yaml` per [ADR 0008](../decisions/0008-self-initializing-single-compose.md). It amends decision 3, withdraws the controller bundle on delivery and supersedes the PORTABLE-COMPOSE-001 description, criteria 2 and 3 and the upgrade part of criterion 4 (restatement recorded on delivery). It is a new release-candidate blocker until delivered, making nine | Operator decision: the installation must be one Compose deployable in a manager such as Dockhand, without host commands | Operator |
| 2026-11-21 | WF-09 | Registered as a required workflow enabler: exactly two tracked Compose files (`compose.yaml`, `compose.dev.yaml`); workflow stacks are derived from `compose.dev.yaml` at run time. No `features.json` entry, like WF-01 to WF-07. No status or class change | Fifteen tracked Compose files make the authoritative one unclear | Operator |
| 2026-11-21 | CUTTING-001, UI-SYSTEM-001 | RC-SEQ-01 resolved: both move from `in_progress` to `implemented`, not `verified`; `verified` requires formal `G-CORE` and `G-UX` acceptance on RC images and operator acceptance. U02 accepted for the non-Preview clauses of `UI-SYSTEM-001 #9` subject to RC `G-UX`; UI-FLICKER-001 observations become `G-UX` measurement items. No class change ([decision record](evidence/uat-operator-feedback-intake.md#operator-decisions-recorded-2026-11-21)) | The release-candidate check blocked protected RC publication on certification that can only happen on RC images | Operator |

## History

The roadmap that preceded this scope, including the PRE-0.1 freeze path, the v0.1.0 release gates
and the beta framing, is kept with its text unchanged at
[history/product-roadmap-2026-11-11.md](history/product-roadmap-2026-11-11.md). The beta
acceptance contract remains at [beta-foundation-001.md](../archive/BETA-FOUNDATION-001/beta-foundation-001.md).
