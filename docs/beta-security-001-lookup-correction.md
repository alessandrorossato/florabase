# BETA-SECURITY-001 draft lookup correction

Independent Claude QA: CONDITIONAL PASS on HEAD 34cebbe901540a0aabd74da969cdeae2e0179a9c,
tree 8653d1a469bad38f68c822d03ef03eabffe0062e. Remediation/security gates accepted;
P1 draft lookup blocks canonical FULL. This correction is ready for targeted independent delta QA,
not publication or canonical verification approval.

## Correction and ordering

The authenticated GH_TOKEN request now lists releases with explicit GET, --paginate and --slurp.
Exactly one release may match the intended tag, and it must be a draft. It is fetched again by
positive numeric ID. Both responses must retain that ID, tag, draft=true, expected repository API
URL and exact approved source SHA as target_commitish. Draft creation explicitly supplies --target
GITHUB_SHA; the existing protected-tag/source/clean-tree checks remain authoritative. Returned asset
IDs must be positive and unique, with state=uploaded. The existing name/size/SHA-256 completeness
checks run before publication. PATCH targets the validated numeric release ID, never a tag lookup.
API errors and stale/missing/ambiguous/published releases fail closed, leaving no publish request.

[GitHub API documentation](https://docs.github.com/en/rest/releases/releases) distinguishes published
tag lookup from authenticated draft listings. Existing publish-job contents:write supports draft
visibility and publication; verify remains read-only. No new permission or token scope was added.
All protected environment, approval, workflow, scanner, attestation and immutable digest gates remain.

Local release asset enumeration, regular-file checks and hashing now run before GHCR version tag
promotion. Source archive and release notes are prepared first. Successful authenticated release
listing is already required before candidate uploads by the existing source preflight. Actual remote
draft/assets cannot be revalidated before they exist: creating/uploading the draft still follows image
promotion and all attestations. Network/API races, upload failures and later permissions failures can
still leave candidates/version tags or a private draft. No cross-service transaction or automatic
retry/overwrite/deletion is claimed. The correction does not redesign that pipeline; final release
remains unpublished on validation failure. Operators must prevent concurrent release edits.

## Focused evidence

Baseline: 21 release tests pass. New regressions against the reviewed implementation: two expected
failures in 23 tests (missing draft-list lookup and forbidden published-tag endpoint). Executing the
actual old workflow Python snippet with the documented draft-tag 404 reproduces the failure without
any publication call; the corrected snippet locates a draft on a later page, re-fetches ID 42,
checks real asset metadata and requests PATCH for ID 42. All API/mutation calls are mocked.
The retained workflow regression also proves incorrect asset digests prevent PATCH.

Final release suite: 25 tests, including pagination, tag-404 behavior, absent/duplicate/published/stale
drafts, source/ID/URL mismatch, API errors, unauthenticated refusal, asset failures, pre-promotion local
validation and prior security/smoke publication-failure tests. Workflow-check covers Ruff, format and
strict mypy; actionlint 1.7.12 covers CI/release YAML with shellcheck integration disabled. Logs are
local /tmp/beta-draft-{before,workflow,actionlint,realistic-probe}.log. No hosted API call, release,
registry write, settings change, source image rebuild or rescan is claimed for this release-tool-only
correction. Canonical FULL remains prohibited pending targeted independent delta QA authorization.

## Separate PostgreSQL maintenance task — operator approval required

Unchanged image remains 2 CRITICAL / 26 HIGH per independent QA; digest and every VEX approval field
are untouched. Publication remains blocked. Carry forward PostgreSQL maintenance as a separate task
coordinated with BETA-RUNTIME-001, with explicit operator approval of scope, exact image identity and
maintenance window before implementation/deployment. The detailed independent reviewer's recipe was
not included in this correction request; do not infer approval of a particular rebuild or VEX.

Proposed task boundary from the existing security handoff: review a maintained fixed image or controlled
same-PostgreSQL-version rebuild with pinned fixed curl/Brotli and reviewed gosu/Go inputs; retain raw
scans and provenance; verify extensions/authentication/compatibility and paired backup/isolated restore.
Agree the release-input/manifest identity transition and rollback/recovery plan with BETA-RUNTIME-001
before changing contracts or any live storage. No automatic PostgreSQL version refresh, runtime code
change or VEX acceptance belongs to this correction. Host approval, protected environment/package
configuration, explicit publication authorization and subsequent release evidence also remain open.
