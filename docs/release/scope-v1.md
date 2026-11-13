# Florabase v1.0.0 release scope

This is the authoritative release contract for v1.0.0. It records what the operator approved on
2026-11-13, what must be true before the release, what is excluded, and how the scope can change.
Where another document disagrees with this one about v1.0.0 scope, this one applies.

Baseline: `main` at `947d77fc8bd2a757cdf49e28ec2e0f85b0374f1b`. A scope entry is not evidence that
work is implemented or verified; increment status stays in [`features.json`](../features.json) and
its reconciliation against this scope is in the
[feature reconciliation](feature-reconciliation-v1.md).

## Operator-approved decisions

| # | Decision |
| --- | --- |
| 1 | **Release line.** The existing private beta (`v0.1.0-beta.N`) is followed by `v1.0.0-rc.N` and then `v1.0.0`. There is no intermediate public 0.1 stable release. |
| 2 | **No new domains.** No new roadmap domain is mandatory before 1.0. |
| 3 | **Installation.** Portable Docker Compose on linux/amd64 is the official installation. Building from source is for development only. The controller bundle is advanced and best-effort; it is not a separately certified installation path. |
| 4 | **Compatibility.** 1.0 supports documented database upgrades, paired database and media backups, and the documented CSV contracts. Compatibility of the HTTP API for outside clients is not guaranteed. |
| 5 | **Care entries.** Journal kinds for watering and feeding are wanted before 1.0. They are dropped from 1.0 if their implementation or migration risk threatens the release. |
| 6 | **Cuttings.** Cuttings is finished and certified, not hidden. |
| 7 | **Performance.** Thresholds are set from fresh measurements. No number is adopted before it is measured. |
| 8 | **Soak.** The first release candidate runs 14 days of real use. The period is extended if a meaningful incident or an unresolved risk appears. |

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
- **Data safety.** Application startup never migrates. No volume is deleted without exact
  identity proof. No shared-daemon prune is automated. Destructive actions keep their explicit
  confirmations.

## Release gates

Each gate is evaluated on one release-candidate commit and recorded with the commit, host,
dataset, command or procedure, result and the operator's acceptance. A gate without a record is
not met. No gate has a record at the baseline.

| Gate | Acceptance criterion | Verification method |
| --- | --- | --- |
| G-SCOPE | Every feature entry in scope is `verified`, or is recorded as post-1.0, best-effort, tooling or historical in the reconciliation; no in-scope entry is `in_progress`. | Feature reconciliation updated for the candidate; `scripts/check-features.py` passes. |
| G-VERIFY | The candidate commit has a fresh full canonical receipt with no reused stages, and the protected checks are green on that commit. | `env -u REUSE FRESH=1 make verify-full`; `feature-tree-fingerprint.py verify`. |
| G-MIGRATE | An empty database reaches the candidate head. A database at the head of the last published beta, holding data, reaches the candidate head. The application refuses to start on any other revision. | Migration cycle; one recorded upgrade from the published beta schema; `florabase.db.release_schema`. |
| G-INSTALL | On a host that has never held the source, the published assets are downloaded and verified, and the [portable installation guide](../portable-installation.md) is followed without any step outside it, ending in a healthy stack, a bootstrapped owner, a sign-in, one created record and one uploaded photo. | Recorded run on one clean Linux host and on the operator's Synology host. |
| G-UPGRADE | From the previous published release with data: paired backup, explicit schema upgrade, healthy stack. Then rollback by restoring the pre-upgrade pair with the previous images into fresh paths. Records and media digests match the source. | Recorded run on a real host. |
| G-RESTORE | A paired backup restored into an isolated project has the same Alembic revision, per-table row counts and attachment digests as the source, and the owner can sign in and open an original. | Recorded drill; `attachment_artifacts.py verify`. |
| G-SEC | Every route except sign-in and the two health endpoints requires authentication, enforced by a test. The image scan has no high or critical finding without a written disposition. Only the frontend port is published. The owner can change the password and recover from a lost one. A vulnerability reporting channel is published. | Tests; the release workflow's scan; a port probe from a second host; `SECURITY.md`. |
| G-DATA | The Golden baseline verifies on the candidate images. A CSV export re-imported through the documented columns loses nothing. | `golden_dataset.py verify-baseline`; one round-trip check. |
| G-CORE | The core acceptance script below passes on the candidate images, starting from an empty database. No open critical or high functional defect. | Recorded operator pass; automated where a browser smoke test exists. |
| G-UX | For the frozen page inventory: no horizontal scroll at 390, 1024 and 1440 px; every control is operable by keyboard with visible focus; dialogs trap and return focus; the shipped themes meet 4.5:1 text contrast; the application is usable at 200 % zoom. | Recorded matrix per page on the candidate. |
| G-DIAG | Every error response carries a code and a message. Every server error is logged with an identifier that the interface shows. The installation guide's troubleshooting covers a wrong origin, a schema revision mismatch, an unhealthy container, bind-mount permissions and a lost password. | Tests; documentation review against that list. |
| G-PERF | The measurement protocol in [PERF-001](../performance/PERF-001.md) is re-run on the candidate images with the Golden COMPREHENSIVE dataset. The operator sets thresholds and the supported collection size from those results, and the candidate meets them. | Published measurements and the operator's recorded thresholds. Until then no threshold exists (decision 7). |
| G-DOCS | The README, installation, upgrade, backup and restore, troubleshooting, user guide, changelog, versioning policy and data-source notes exist, match the candidate, and were the only instructions used in G-INSTALL, G-UPGRADE and G-RESTORE. | Those runs; a link check. |
| G-DIST | The tag, images, Compose asset and release manifest identify the same commit; attestations verify; every version surface agrees. | The protected release workflow and its checks, applied to the release-candidate channel. |
| G-SOAK | The operator's real collection runs on a release candidate for 14 days with no data-loss incident and every incident triaged. A meaningful incident or unresolved risk extends the period (decision 8). | The operator's log. |

### Core acceptance script (G-CORE)

1. Empty database: sign in, see a usable empty Today, follow the path to a first record.
2. Botanical identity, profile and a manual native range.
3. Supplier, order and a seed lot with partial and unknown values.
4. Sowing, germination observation, plant and plant group, extraction and a supported reversal.
5. Journal entry with each date choice; photo upload; primary photo.
6. Bulk move; label print preview and QR lookup.
7. Schedule an activity, complete it, and see Today reflect it.
8. Harvest, stored material and a new seed lot; the lineage view shows the chain.
9. Search, filters and a Saved View; CSV export and import preview.
10. Session expiry during an edit and a server stop during a save: an error is shown and nothing is lost.
11. Change the password and sign in with the new one.
12. Cuttings: a material lot through rooting to an established plant, including a failed and a still-unknown attempt (decision 6).

## Work required before v1.0.0

Identifiers are stable. Each becomes a feature entry when its increment is selected.

### Engineering

| ID | Work | Why |
| --- | --- | --- |
| ENG-01 | Owner password change, and an offline reset command | There is no change or reset operation in `backend/src/florabase/auth/`. |
| ENG-02 | Baseline security headers in the bundled nginx | `frontend/nginx.conf` sends none. |
| ENG-03 | A test that every route requires authentication | Coverage is complete at the baseline and unguarded. |
| ENG-04 | Request identifier logging and an unhandled-error log | Needed by G-DIAG. |
| ENG-05 | Fix or formally accept the two TAXONOMY-001 concurrency findings | Recorded open in `progress.md`. |
| ENG-06 | A real-browser smoke test on the production images | Supports G-CORE; desirable, not a gate by itself. |
| ENG-07 | Performance re-measurement and the supported-size statement | G-PERF. |

### Development workflow

These do not change the product. They are in scope because the release work depends on them.

| ID | Work |
| --- | --- |
| WF-01 | Stop idle Quality networks from consuming Docker address pools |
| WF-02 | Separate product-wide verification from workflow verification, without narrowing any product check |
| WF-03 | Own tests by directory and run the inventory check before the gate |
| WF-04 | A documented batch integration profile with provenance and retirement |
| WF-06 | A report-then-confirm command to retire resources of finished work |
| WF-08 | Remove duplicated post-merge CI runs |

### Functional

| ID | Work | Decision |
| --- | --- | --- |
| FN-01 | Finish and certify Cuttings | 6 |
| FN-02 | Sorting in the Seeds, Sowings and Plants directories | — |
| FN-03 | Watering and feeding Journal kinds; dropped if they threaten the release | 5 |
| FN-04 | Searchable pickers for large reference lists | — |
| FN-05 | Resolve UX-DATE-001 decision D1 (below) | open |
| FN-06 | Verify the empty-database first run and fix what it shows | — |
| FN-07 | Verify PWA installation on physical devices, or label it experimental | — |

### Documentation and distribution

| ID | Work |
| --- | --- |
| DOC-01 | One official installation guide for portable Compose, with a proxy example and troubleshooting; source-build and controller guides labelled per decision 3 |
| DOC-02 | Feature graph reconciliation (this increment) and the `release_target` schema ([follow-up](release-target-schema-followup.md)) |
| DOC-03 | Correct remaining stale statements in engineering documents |
| DOC-04 | An end-user guide |
| DOC-05 | Changelog, versioning policy and a vulnerability reporting channel |
| DOC-06 | Documentation reorganisation and archive |
| REL-01 | A release-candidate and stable channel in the release tooling |
| REL-02 | The real-host runs for G-INSTALL, G-UPGRADE and G-RESTORE |
| REL-03 | Release candidate, soak and release |

## Open decision: UX-DATE-001 D1

The decision is recorded as unresolved in `progress.md` ("D1 is unresolved: a new entry starts
with no choice and Save is refused until one is made") and in the code
(`frontend/src/events/OccurrenceDateChoice.tsx`, prop `newEntryDateChoice`). The design handoff
states it as: *in the Journal composer, is Today preselected or must the user choose?*

| Alternative | Behaviour | Stated trade-off |
| --- | --- | --- |
| (a) Nothing selected | A new entry opens with no date choice; saving is refused until Today, Another date or Date unknown is chosen. | One more tap; a wrong day cannot be recorded by inattention. |
| (b) Today preselected | A new entry opens with Today chosen. | Faster; defensible because today is not a historical date. |

The design handoff recommended (a) and asked for the default to be a prop so that the decision
could change without rework. The delivered code implements (a) as that default. No operator
decision is recorded for either alternative.

## Excluded from v1.0.0

Recurring care plans; plant health workflow; contextual entity timelines; QR quick capture;
receiving and order lines; calendar export and reminders; full portable export (TRANSFER-001);
user-provided phylogeny; PHYLOGENY-001 and BOTANY-003 (source-blocked); BOTANY-004;
ENRICHMENT-002; TUBER-001; WEATHER-001; ANALYSIS-001; DASHBOARD-CUSTOMIZATION-001; SECURITY-003;
INTEGRATION-001; offline changes; arm64 images; an HTTP API compatibility promise; botanical
matching beyond the read-only foundation; certification of the source-build and controller paths.

These stay described in the [product roadmap](../product-roadmap.md). None of them becomes a
release dependency without a scope change.

## Changing this scope

1. A change is proposed as a record appended to the table below: the date, the affected
   identifier, whether it is added, removed or re-targeted, the reason, and what it costs or saves.
2. Only the operator approves a record. An agent may propose one and must not act on it first.
3. An approved record is delivered as a documentation change to this file.
4. Work that is not in this file and not covered by an approved record is post-1.0.

| Date | Identifier | Change | Reason | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-13 | — | Scope established | Operator approval of the pre-1.0 audit direction | Operator |

## History

The roadmap that preceded this scope, including the PRE-0.1 freeze path, the v0.1.0 release gates
and the beta framing, is kept with its text unchanged at
[history/product-roadmap-2026-11-11.md](history/product-roadmap-2026-11-11.md). The beta
acceptance contract remains at [beta-foundation-001.md](../beta-foundation-001.md).
