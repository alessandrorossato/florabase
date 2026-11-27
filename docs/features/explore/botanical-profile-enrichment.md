# Controlled BotanicalProfile text enrichment — approved, blocked

BOTANY-003 remains **planned**. The [2026-10-09 source decisions](botanical-profile-enrichment-sources.md)
confirm WCVP geographic text eligibility, reproduce the WFO / Flora of China TLS blocker, and approve
only three exact Kew SEPASAL / Flora Zambesiaca descriptions. Those three records are insufficient
coverage for general description enrichment. No text proposal API, Apply, provenance persistence or
enrichment UI has been implemented.

Canonical BotanicalProfile still has five optional sections: description, origin_distribution,
cultivation, uses and warnings. Source evidence must remain separate from those canonical fields.
ENRICHMENT-001 owns structured native ranges; BOTANY-003 must never derive them from prose or
create distribution prose from source assertions or drawing geometry.

The complete [approved contract](botany-003-audit.md#31-approved-productsource-decision) remains:

- Only the three source records explicitly allowlisted in the [source decision](botanical-profile-enrichment-sources.md)
  currently have description source GO. WFO / Flora of China still requires secure acquisition and
  current source verification before use. Kew WCVP geographic_area proposes origin_distribution.
  Every source requires exact reviewed provider identity and retained source, version, retrieval,
  checksum, element license and reference. Multiple descriptions stay separate; the three SEPASAL
  records are not sufficient coverage for broad BOTANY-003 implementation.
- Explicit retrieval freezes proposals against current canonical fields; it never writes profile
  content or creates an empty profile. Optional missing source data never prevents normal startup,
  identity creation, manual editing, native ranges or collection workflows.
- Review shows Current, Proposed, Source/version, attribution and field-specific action. Populated
  fields default to Keep current and require concrete Replace confirmation. Empty fields still
  require explicit Apply. Apply all available may select only displayed empty-field proposals;
  nonempty replacements require separate explicit intent. Identical value/source evidence is no change.
- Immutable typed applications retain field, previous/applied values, provider/dataset/version,
  exact taxon/reference, license/citation, retrieval/application times, actor where available and
  destination revision. Each field has an explicit current application association. Manual change
  clears only that field's association; unrelated edits preserve it and history never changes.
- Field-level monotonic destination revisions must cover all canonical writers, deletion/recreation
  and edit-and-restore. Locked Apply rechecks source/link/identity/destination and rejects stale
  selections atomically; concurrent Apply must retain exactly one application. No prose merging.
- Reprovisioning or source updates never reinterpret an old proposal or edit applied text. Link
  changes, source removal and manual edits preserve immutable historical evidence. The future exact
  frozen-source Apply policy must be documented separately from ENRICHMENT-001's range policy.
- After successful identity creation, offer an optional Review botanical information step and Skip
  for now. The identity already exists regardless of source failure. Existing identities expose
  Check trusted sources for explicit later retrieval. These entry points remain unimplemented.
- Authenticated reads; owner/Origin/CSRF-protected writes; fixed official provisioning only, no
  arbitrary fetch. Validate download size/time/checksum, archive members/decompression/paths,
  encoding/schema/IDs/references, markup conversion and the existing 20,000-character limit.
- A new Alembic migration is required for text evidence/revisions. Current head remains 0039;
  0040 is the next available sequence, not a migration created by this audit. Populated downgrade
  must refuse loss of meaningful source evidence. Startup never migrates or downloads source data.
- Review stacks Current/Proposed/source/actions on mobile, labels choices, provides readable long
  text and attribution, and focuses useful conflict feedback. Validate 1440×844, 1024×844, 390×844.

Cultivation, uses and warnings remain manual pending the [separate source audit](botanical-knowledge-source-audit.md)
and a future reviewed increment. Automatic refresh, taxonomy, phylogeny and broad visual redesign
remain outside BOTANY-003. The [blocked handoff](botany-003-handoff.md) records what actually ran.
