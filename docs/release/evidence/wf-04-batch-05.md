# WF-04 Batch 05 integration evidence

Base `ed5747c20d181c93b5cf78dab1656a24c576ba9b`. The writer is
`sol-batch05-integration` (claim `8908b4edd6b0`). The approved title is
`chore(release): Cuttings completion and UX fixes (batch 05)`.

The [batch manifest](batches/batch-05.json) records the pinned sources, claims, independent
source reviewer, merge order and resolutions. The approved request orders UX first and Cuttings
second. Sol reviewed both component sources in a separate OpenAI Codex session before taking the
integration claim. That review covers the source tips below. Independent combined review is pending.

| Source | Frozen tip | Independent source verdict |
| --- | --- | --- |
| [UX F-01 through F-05](rc-gux-functional-defects.md) | `b3491620076afdf1aec44b67637365a1312e2182` | PASS, `sol-codex-source-qa` |
| [FN-01 Cuttings](fn-01-source.md) | `418b38647024f906d4ab0b52233e32b193eae7cf` | PASS, `sol-codex-source-qa` |

WF-04 replayed the UX merge as `854c624ebe4da8f80100e00a14730eccc61da55a`
and the Cuttings merge as `76a76203f59da7d6e435e8d0dbfe257ac2e1c0f5`.
The only conflict was additive in `docs/progress.md`. Both milestones are preserved.
Reconciliation distinguishes Hydrogen's CDP viewport and DPR emulation from Sol's separate
native Chromium 200% source QA using `chrome.tabs.setZoom(2)`.

## Focused combined checks

- Vitest passed 245 tests in eight files covering the app, responsive CSS, ReferencePicker,
  seed lots, Journal, EventFeed, Cuttings and UX001.
- The disposable PostgreSQL Cuttings, History and Schedule suites passed 56 tests.
- Authenticated Chromium smoke passed in the isolated combined app. It covered the six
  directories at emulated `720×422` CSS pixels at DPR 2, desktop sanity at `1440×844`
  and `1024×844`, and mobile pagination, Gallery, filter chips and identity tabs at
  `390×844`. First Escape closed the ReferencePicker and retained combobox focus and the
  parent dialog. Second Escape closed the parent. No unexpected browser, console or request
  errors were recorded. Ownership-checked cleanup left no disposable resources.
- `make api-generate` reproduced both committed declarations byte-for-byte. `make api-check`,
  `make lint`, `make format-check` and `make typecheck` passed.
- The feature graph, offline documentation links and whitespace checks passed. The RC checker
  still reports the same eight blockers as pinned main.

## Remaining acceptance

CUTTING-001 and FN-01 acceptance remains pending, including G-CORE step 12 on candidate images.
UI-SYSTEM-001 and formal G-UX remain open, F-06 is deferred, and U04 and R21 remain unresolved.
This batch changes no feature status or release class. Independent combined review of the exact
reconciliation commit precedes the fresh canonical FULL and protected operator delivery.
