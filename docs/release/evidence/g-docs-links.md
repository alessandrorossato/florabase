# G-DOCS offline link check evidence

- Source commit: `0d6149ead8b77f4c90d1e7847da74ef93fdeb859`.
- Host: local Linux workstation; independent detached checkout of that source commit.
- Fixtures: repository Markdown and isolated temporary Markdown parser fixtures; no network or
  production data was used.
- Independent checks passed: repository scan (270 Markdown files before this evidence file), four
  checker regression tests, additional parser boundary fixtures, Ruff lint and format on the new
  scripts, strict mypy on the checker, `scripts/test-verification-impact.py` (37 tests), and
  `scripts/test-feature-workflow.py` (54 tests).
- This is evidence for the link check only. Human review of the release-candidate documentation and
  the G-INSTALL, G-UPGRADE and G-RESTORE runs remain pending. The canonical FULL gate has not run.
