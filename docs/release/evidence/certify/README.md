# Certification evidence maps

Each file maps the committed evidence for one `certify` entry of the
[release-scope manifest](../../scope-v1.json), criterion by criterion, as the
[scope](../../scope-v1.md#certification-of-delivered-features) requires. Every map is written
against `main` `554d74de88a278e2b9a392de9d105d3d62c35f91`.

A map is not certification. It does not change a `features.json` status. It is reviewed
independently, and a status changes only after the gate records it relies on exist for the
release candidate.

How to read the State column:

- **Mapped:** committed tests or records cover the criterion. They still need the canonical gate
  result on the candidate commit.
- **Pending G-UX** or **Pending G-CORE step N:** the criterion relies on that part of the gate
  record, which uses the [G-UX](../g-ux-template.md) or [G-CORE](../g-core-template.md) template.
- **Pending candidate gate:** the criterion itself requires canonical verification.
- **Gap:** no committed evidence, and no planned gate record covers it. It needs new evidence or
  an operator-approved exception.

Evidence that exists only in `progress.md` prose, a worktree receipt, a PR body or outside the
repository is listed as "Not counted" in each map.

| Entry | Status | Mapped | Pending | Gaps |
| --- | --- | --- | --- | --- |
| [TAXONOMY-002](taxonomy-002.md) | `implemented` | 4/4 | — | — |
| [PHENOLOGY-001](phenology-001.md) | `implemented` | 4/5 | G-UX #4 | — |
| [UI-POLISH-001](ui-polish-001.md) | `implemented` | 4/5 | candidate gate #5 | — |
| [WCVP-DEFAULT-001](wcvp-default-001.md) | `implemented` | 3/4 | candidate gate #4 | #4: no committed independent QA record |
| [WGSRPD-CROSSWALK-V2](wgsrpd-crosswalk-v2.md) | `implemented` | 4/5 | candidate gate #5 | #5: no committed independent QA record |
| [BRAND-01](brand-01.md) | `implemented` | 0/3 | G-UX #2 | #1–#3: no committed record that the artwork is the approved one; the archive manifest is not in the repository |
| [GERMINATION-001](germination-001.md) | `implemented` | 3/3 | — | — |
| [SEARCH-001](search-001.md) | `implemented` | 3/3 | — | — |
| [IMPORT-001](import-001.md) | `implemented` | 3/3 | — | — |
| [LINEAGE-003](lineage-003.md) | `implemented` | 2/3 | G-UX #3 (the captures predate Cuttings) | — |
| [LOCATION-003](location-003.md) | `implemented` | 3/4 | G-UX #3 (restated by R25) | — |
| [GEOGRAPHY-003](geography-003.md) | `implemented` | 2/3 | G-UX #3 (restated by R13) | — |
| [MEDIA-VISUAL-001](media-visual-001.md) | `implemented` | 4/5 | G-UX and candidate gate #5 | — |

Gaps need an operator decision. Either commit the missing record, such as an independent QA
report or the approved-artwork manifest, or record an exception.
