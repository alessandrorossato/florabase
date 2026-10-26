# Taxonomy visual implementation Review

This is a candidate-owned synthetic Review, not an authoritative WFO installation.
Its actual frontend, FastAPI backend and PostgreSQL database belong to
`feat/taxonomy-visual-001`. No full WFO archive is downloaded. Fixture IDs beginning
`wfo-900…` must never be copied into production links.

Open **http://localhost:15278/#/taxonomy?taxon=wfo-9000000008**.
Credentials are in the ignored, owner-readable `.taxonomy-review/credentials.json`
in this worktree. Do not publish that file or paste its password into the handoff.
The account is labelled **Taxonomy Review (synthetic)**.

## Reproduce

Run from this worktree:

```sh
python3 docs/review/taxonomy-visual-001/review.py up
python3 docs/review/taxonomy-visual-001/review.py seed
python3 docs/review/taxonomy-visual-001/review.py status
python3 docs/review/taxonomy-visual-001/review.py check
```

The helper reuses repository ownership validation and migration handling with its
own project, loopback port, network, DB, media and dependency volumes. It refuses
foreign ownership. Seeding refuses an unrecognized nonempty collection, and a
repeat seed retains operator edits. No stop/remove/reset action is provided.
The generic Review status line reports the standard fixture as missing because
this scenario has its own checked ledger; the following synthetic fixture status
is authoritative for this Review.

`runtime.py` builds the tiny local SQLite source through the delivered index
builder. Only its explicitly selected `serve` command overrides the source
dependency. Production startup and provider code never import these tools.
The synthetic version and citation remain visible in the actual API and UI.

## Final UX refinement (2026-10-26)

[Current gallery](final-ux/gallery.html) includes the compact header, List/Tree
switch, KPI popovers, unified facets and native fullscreen. All six themes and
requested widths are captured. Stored thumbnail absence is not interpreted as
absence of a remote cover link. The existing 12-identity fixture and operator
confirmations are preserved; no new seed, WFO install or backend change is needed.

## Tree Explorer extension (current Review)

Open **http://localhost:15278/#/taxonomy?view=tree&taxon=wfo-9000000008**.
The original eight identities and operator-confirmed links were preserved. The
additive `enhance.py` fixture added four marked identities: generic Basil, Thai
Basil, unlinked Mentha and unlinked Melissa. Current totals: **12 represented,
10 placed, 2 unresolved; Living 5, Current 9, Historical 3**, three placed families.
Basil has three identities (Living/Current/Historical) sharing one taxon; generic
Basil and Genovese share one real asset; Thai has no cover. Aloe has another asset.
Three cover relationships use two credited small local photographs; see
[media credits](media/README.md).

To reproduce the additive extension after the original seed, run
`python3 docs/review/taxonomy-visual-001/review.py enhance`. This uses the same
`TaxonomyReview` ownership validation and executes `python /review/enhance.py` in
its backend. A fresh fixture retains its original unresolved links in addition to
the two new ones; the current placed count reflects operator confirmations. It checks the runtime, ledger and database name, refuses conflicting
non-fixture identities, preserves existing covers and never resets operator links.
After completion it retains the fixture without rewriting it. The candidate source
remains tiny and synthetic. No protected environment or full WFO dataset is used.

[Tree gallery](tree/gallery.html) includes the new graph evidence. The following
original Classification scenarios and screenshots describe the earlier eight-row
fixture; their original unresolved counts are historical, not the current totals.
Do not replay the original write-based API scenario against operator-confirmed
Lavender links merely to reproduce its earlier two-unresolved state.

## Original Classification scenarios

- **Available:** eight represented identities, six placed, two unresolved; five
  Living, seven Current, one Historical; three placed families. Inspect Basil and
  Rosemary. Rosemary retains its local name and a confirmed synonym association
  with the accepted Salvia rosmarinus concept. Full paths include intermediate ranks.
- **Absent:** run `review.py source unavailable`, then use **Retry source**.
  All eight local identities remain accessible, the classified tree is absent,
  and selected identities retain stored confirmation evidence. Run
  `review.py source available` and retry to restore exploration.
- **Concurrent edit:** open Needs review, select Lavender, search **Lavandula**
  and inspect the exact species candidate. Run `review.py conflict`, then confirm
  in the browser. The server rejects the old timestamp. **Refresh identity and
  review again** reads the actual identity, clears candidate state and requires
  another search, inspection and explicit confirmation. This command edits only
  the managed synthetic Lavender identity. Confirmation does not rename it.
- **Live HTTP proof:** `python3 docs/review/taxonomy-visual-001/api_scenarios.py`
  exercises authenticated source-ready/absent reads, retained synonym evidence,
  blank-prefix rejection, stale identity 409, authoritative GET, renewed search,
  explicit confirm and version-guarded unlink. It refuses to replace an operator's
  Lavender link, restores its original local fields, leaves eight identities and
  two unresolved links, restores source availability and logs out its own session.

These are real HTTP/database writes against disposable synthetic data. The HTTP
script does not establish visual, touch or assistive-technology acceptance.

## Operator checks

Use Settings to select Botanical, Herbarium or Mineral and Light/Dark. Inspect at
1440×844, 1024×844 and 390×844. Check the Filters drawer, separate tree disclosure
and selection, the full source path, exact identity links and Return to Taxonomy,
browser Back/Forward/reload, Needs review, source absence and conflict recovery.
Living + Seeds is empty; multiple record categories use OR; no category means all.
Counts are distinct eligible identities, not physical plant quantities.

See [the implementation handoff](../../taxonomy-visual-001-handoff.md) and
[capture gallery](gallery.html) for evidence and remaining limits.
