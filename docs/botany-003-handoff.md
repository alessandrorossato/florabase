# BOTANY-003 source decision handoff — 2026-10-09

**DESCRIPTION_SOURCE_GO — narrowly scoped Kew SEPASAL / Flora Zambesiaca alternative.**
Three exact English general-description records are approved; Flora of China remains blocked by
its file-host TLS chain. The latest request authorizes investigation only: **implementation remains
stopped**. BOTANY-003 remains **planned**. This is not READY_FOR_VISUAL_REVIEW.

## Worktree

- `/home/alessandro/.codex/worktrees/857e/florabase`, branch `feat/botany-003-profile-enrichment`.
- Initialized through `make feature-init` from clean detached current cached origin/main
  `345e9f25eed7590c230bdee65c7ff06d34d8304a` (ENRICHMENT-001 delivered through PR #79).
- Only documentation/feature planning changes, deliberately unstaged/uncommitted. No other checkout
  was edited. No feature-verify, staging, commit, push, delivery, merge or finish was run.

## Final bounded fallback / description decision

[Audit section 35](botany-003-audit.md#35-final-bounded-official-source-fallback--2026-10-09)
is the current description-source decision and supersedes the earlier overall source blocker only
for this exact alternative. No production code or feature status changed. This follow-up modified
only the audit and handoff; eight other previously changed documents were preserved by hash check.

- Exact primary artifact:
  [sepasal_notes_references.csv](https://sftp.kew.org/pub/data-repositories/sepasal/data/sepasal_notes_references.csv).
- Snapshot: publisher's discontinued static export, **no numbered release**. CSV Last-Modified
  **2020-09-23 16:12:04 GMT**, independently retrieved **2026-10-09T13:07:03.610025Z**,
  **30,762,595 bytes**, SHA-256
  `5c900968f31382f6afb283aa0dfbb01234f9695576565d4c109a3fadee2a905c`.
  Audit section 35 pins the exact URLs/checksums/access times of README, taxa and reference files too.
- Schema: UTF-8 CSV `TaxKey, NoteCatKey, NoteCatText, NoteKey, NoteText, BiblKey` plus the exact
  bibliography fields listed in the audit. `NoteCatKey=9`, `NoteCatText=BOTANICAL DESCRIPTION`.
  **94,084** complete note-reference rows; category 9 has **183 rows / 177 notes / 165 TaxKey**.
  Exact joins resolve to **6,988 taxa / 17,853 name rows** and **4,951 distinct bibliographies**;
  all category-9 embedded reference fields agree with the separate reference table.
- Approved allowlist: **TaxKey/NoteKey/BiblKey** `78/104262/5701`, `624/98287/5701`,
  `1152/98358/5701`; respectively source labels Cleome gynandra, Grewia mollis and Rhoicissus
  tridentata. The audit pins each exact text hash and source NamKey. Full English botanical prose
  was manually reviewed; text/control/length validation passed without repair or translation.
- License: [Kew's directly retrieved dataset-specific README](https://sftp.kew.org/pub/data-repositories/sepasal/README.txt)
  states **CC BY 4.0 for SEPASAL data**. The three notes/reference have no contrary notice; the
  schema has no per-record rights field. GO covers the text republished in this export, with Kew's
  requested SEPASAL citation, access time, [license link](https://creativecommons.org/licenses/by/4.0/),
  original **Flora Zambesiaca reference 5701 / Royal Botanic Gardens, Kew**, source URL and retained
  notices/change indications. It does not license other providers, images or underlying books.
- Taxon linkage: snapshot-qualified literal **TaxKey**, with **NoteKey/BiblKey** for record evidence,
  deterministically joins source tables. No WFO/GBIF/WCVP crosswalk is established. Future association
  to Florabase requires an **explicit reviewed exact SEPASAL TaxKey link**; no name matching or
  numeric-ID conversion. Current provider/link infrastructure does not implement this new source.
- Coverage: selected dryland economic plants worldwide, historical and discontinued; **three
  approved records**, not global coverage or a default. All other records remain unapproved. Some
  category-9 records are citation pointers, describe related species, or contain invalid control
  characters. BiblLang describes bibliography language and cannot establish NoteText language.
  Category 10 fragmented descriptions must not be concatenated. Other profile fields remain manual.

This is a separately approved Kew distribution, **not a mirror of Flora of China**. USDA's official
documentation permits text reuse but this bounded review established no exact machine-readable
general-description artifact; it has no description GO and is not a global default. Another official
WFO flora archive (FTEA) uses the same failing file host and has no fresh content/license approval.

## Flora of China re-audit / remaining specific blocker

[Exact decisions and probe evidence](botanical-profile-enrichment-sources.md) record the official
WFO download/provider investigation. Host curl, existing development and production HTTPX, and
freshly built current-worktree HTTPX all reject the exact Flora of China archive with
CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate, before HTTP headers/body.
A fresh verified OpenSSL probe shows the omitted issuing intermediate and fatal error 20.
The final follow-up explicitly repeated host `curl -Iv` and HTTPX on the normal quality Compose
network against **files.worldfloraonline.org**, not a different WFO hostname, with the same result.
Direct current WFO resource metadata retrieval also failed verification; indexed snippets alone
cannot verify the requested current license, provider, attribution, import mode or snapshot.

Official WFO publisher static release 2026-06 is securely visible as research metadata. Its published
package descriptions establish taxonomy, not replacement Flora descriptions; no secure official
copy of the same FoC resource was established in the bounded investigation. The separate Kew
source above now supplies a narrowly approved alternative. No disabled TLS, custom trust, HTML species scraping,
unofficial mirror, browser acquisition or assumed identifier mapping was introduced.

Historical English/general-description schema, exact WFO/reference joins and CC BY 4.0 eligibility
remain historical approval from the earlier audit. No fresh WFO archive bytes, checksum or retrieval
timestamp were obtained, so no fresh WFO parser/content approval or implementation GO is claimed.

## Origin_distribution source / license, version and checksum

Independently retrieved the fixed official WCVP **v15** plain archive securely at
**2026-10-09T12:32:17.250119Z**, **89,508,082 bytes**, SHA-256
`693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81`.
Complete 1,441,152-row names scan confirms the distinct **geographic_area** text, including exact
Acer, Annona and Aloe source IDs/values. CC BY 3.0/release citation are established by the existing
exact v15 audit; identical plain archive bytes were freshly verified. No prose is built by joining
Native assertions or map geometry. Source-field GO does not make BOTANY-003 implemented.

## Proposal semantics / field provenance

[Approved complete text contract](botanical-profile-enrichment.md) records retrieval-only proposals,
Current/Proposed/source comparison, explicit empty-field Apply, conservative populated-field Keep
and concrete Replace confirmation. Immutable typed field applications and explicit current field
associations must preserve history through manual edits, source replacement/unavailability and
relinking. The earlier approved requirement includes previous/applied values and actor where available.

These text structures are **unimplemented**. Existing ENRICHMENT-001 proposal/application evidence
belongs to structured ranges and cannot be presented as text provenance. Its index also omits
geographic_area; a text source representation would be separate. No empty profile is created.

## Creation-time flow / existing-identity flow

Existing identity creation remains independent of source data. The requested optional post-create
Review botanical information / Skip and later Check trusted sources entry points are documented
acceptance requirements, **not added UI**. No placeholder action promises unavailable text imports.

## Stale / concurrency

Field-level monotonic revisions, all canonical writer coverage, edit-and-restore safety, locked
source/link/identity/destination revalidation and one-success concurrent Apply remain required.
No text stale/concurrency behavior or PostgreSQL proof is claimed. Range revisions are insufficient
for text. Source updates must create new review evidence, never reinterpret an existing proposal.

## Cultivation / uses / warnings audit

[Separate audit](botanical-knowledge-source-audit.md) independently identifies official Kew SEPASAL,
CC BY 4.0, local TaxKey, exact note/use fields and bibliographic references. Three complete verified
CSV inspections cover taxa (17,853 rows), major-use references (3,080) and note references (94,084).
Cultivation and toxicity categories exist; use categories distinguish food, medicines, materials,
environment and poisons. A source-local TaxKey can legitimately have multiple name/reference rows.

This is a credible future source for those three additional fields, with no production-import GO
for their specific field mappings yet. The scoped description GO above is separate.
Historical context, reference/accepted-name joins, coverage and warning statement authority require
review. No data is flattened into advice. All three canonical sections remain manual; no imported
warning implies completeness or safety. BOTANY-004 retains the future source-reviewed work.

## Migration / API / security / UI

No migration, API contract, generated artifacts, production code, source index or UI changed.
Alembic head remains **20261009_0039**; 0040 is not reserved by a placeholder migration.
Future typed text evidence must refuse populated downgrade, remain authenticated with normal
Origin/CSRF, and use fixed bounded secure provisioning and indexed local lookup. No new service.
Long-text comparison, labelled choices, conflict focus, attribution and the three requested viewport
checks remain pending because no BOTANY-003 review UI exists.

## Tests

Earlier focused existing-behavior backend baseline passed: **72 tests**, `--no-cov`, through this worktree's
isolated quality Compose environment:

```sh
python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps backend \
  pytest --no-cov tests/test_botanical_profile_service.py tests/test_botanical_profile_schemas.py \
  tests/test_native_range_enrichment.py tests/test_external_botany_provider.py \
  tests/test_botanical_identity_service.py
python3 scripts/check-features.py
git diff --check
```

Feature graph: **98 valid**, preserving all 95 existing IDs/statuses and adding three planned owners.
The earlier re-audit's pinned Prettier 3.9.6 verification passed for all ten changed documents;
local document links passed. No new production source-parser/proposal tests,
PostgreSQL text integration/migration cycle, frontend tests, API regeneration/drift, static typing,
production build or graphical QA were run in that earlier documentation-only blocked phase.
The quality baseline built its development image from current source. A separate network-disabled
bare import probe lacked required database_url configuration and failed Settings validation; this
is not an app-health test or evidence of a product regression. No full canonical gate/receipt.

## UAT

Read-only `make uat-preview-status` established actual owner
`/home/alessandro/.codex/worktrees/16cc/florabase`, frontend/backend/DB healthy, schema **0039**.
It correctly returns source mismatch from `857e`; BOTANY-003 has **no Preview UI or seeded cases**.
No retirement, reset, seed, takeover or manual Docker-resource removal was performed. The existing
ENRICHMENT-001 review data is preserved while BOTANY-003 implementation remains stopped.
After a real implementation exists, retire through that owning worktree using its guarded command,
then start/seed/status from `857e` and perform the requested synthetic UAT scenarios.

## Taxonomy future / phylogeny future / roadmap

The graph already owns TAXONOMY-001 reconciliation and TAXONOMY-002 name history. The new
**planned TAXONOMY-003** represents the collection-aware taxonomy tree without repurposing them.
[Future contract](collection-taxonomy-plan.md) records collection scopes, family/genus/identity
navigation, distinct counts, WFO static-source candidate and unresolved parent/rank/synonym/link/
version/index questions. Use Taxonomy; collection Lineage retains its existing meaning.

**Planned PHYLOGENY-001** separates evolutionary-tree discovery from classification. Open Tree of
Life is a later candidate only. No branch lengths, MRCA, synthetic retrieval or inference is added.
BOTANY-004 separately preserves other profile-field discovery. Roadmap prioritizes BOTANY-003 then
collection Taxonomy; ENRICHMENT-002 and broad visual/product review remain deferred.

## Stop / future resume boundary

The source investigation now establishes a separately approved official description artifact for
three records. **Do not implement in this turn.** The next authorized implementation must preserve
its exact snapshot/record eligibility, license and explicit TaxKey linkage, alongside independently
approved WCVP geographic text. No unreviewed record or license can be silently enabled.
Reproduce all requested real-PostgreSQL, security, creation/later UX, responsive and synthetic UAT
cases before claiming implemented or READY_FOR_VISUAL_REVIEW. Flora of China remains unavailable
until normal TLS acquisition and current metadata/content/license verification succeed.
No weakened TLS or source trust exception is requested or authorized.

Follow-up checks: complete source CSV scans and exact selected-note hashes/validation passed;
audit/handoff Prettier check, feature graph and `git diff --check` passed; eight other prior changed
documents were hash-compared unchanged. No application tests were rerun during this source-only
follow-up, and no canonical gate, staging, commit, push or UAT operation was performed.
