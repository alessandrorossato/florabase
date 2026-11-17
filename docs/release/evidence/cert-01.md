# CERT-01 — certification documentation source

Branch `docs/batch-03-certification`, writer `claude-doc-batch03`. It was started from `main`
`554d74de88a278e2b9a392de9d105d3d62c35f91` and reconciled with `main`
`836bf80305a19fdd7f49845b8bc00ae423553a93` after Batch 02 (#192). The change is documentation
only, and the verification plan selects the docs tier.

## Content

- [`restatements-v1.md`](../restatements-v1.md): 14 confirmed and 11 proposed restatements,
  3 open gaps, and the COLLECTION-VISUAL-002 open items.
- Two scope-change rows in [`scope-v1.md`](../scope-v1.md):
  - R24, UI-SYSTEM-001 #4: four Today photos.
  - CERT-01 to CERT-04 registered as `tooling`.
- Thirteen evidence maps and an index under [`certify/`](certify/README.md).
- The [G-UX](g-ux-template.md) and [G-CORE](g-core-template.md) record templates.
- The centered README logo. The asset `docs/assets/florabase-logo.png` is unchanged.
- The CERT-01 to CERT-04 entries in `docs/features.json` and `docs/release/scope-v1.json`.

No existing status or release class changes. Nothing is certified.

## Focused checks

All of these were run on the reconciled source:

- `python3 scripts/check-features.py`: 167 valid.
- `python3 scripts/check-features.py --release-candidate`: the same eight blockers as `main`.
- `python3 scripts/check-doc-links.py`: 291 documents passed.
- `python3 scripts/test-doc-links.py`: OK.
- `python3 scripts/test-beta-runtime.py Disclosure -q`: 63 tests passed.
- `git diff --check`: clean.
- `make verification-plan`: docs tier; static checks feature-graph and whitespace.

## Independent review

The reviewer `claude-qa-cert01` worked read-only from separate exports and was not the writer.

| Reviewed commit | Verdict | Notes |
| --- | --- | --- |
| `d46e712` | FAIL | One major: four restatements confirmed on delivered features only. Six minor. |
| `72b39da` | PASS | All seven fixed; two minor left. |
| `5b71bbd` | PASS | A contradictory cell in the GEOGRAPHY-003 map fixed. |
| `3b7ebc2` | PASS | CERT-01 to CERT-04 registration meets the operator's conditions; blocker list unchanged. |
| `2688f46` | PASS | Merge with `836bf80` and reconciliation correct; two drifted citations noted (PHENOLOGY-001, BRAND-01). |

The commit that adds this record fixes those two citations. Its own review verdict is given to
the batch integration writer with the exact source tip.
