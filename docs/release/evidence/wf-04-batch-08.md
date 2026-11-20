# WF-04 Batch 08 integration evidence

Pinned main is `4eeaa9badba9353d2608bf62fee703057d10dcb9`, which includes the
BETA-SECURITY-001 nginx 1.30.7 frontend base (PR #198) and Batch 07b (PR #199). The
integration writer is `claude-batch08-integration` with claim `09b71e9b439d`. The
[manifest](batches/batch-08.json) records the exact commits, bases, original source claims,
reviewers and merge order.

| Source | Frozen tip | Source approval provenance |
| --- | --- | --- |
| ENG-03 | `c43b4161275181b45e33ebc86dbe08794c405e34` | Hydrogen PASS WITH NOTES, `hydrogen-batch08-eng03-qa`, on tree `89dad69a`. Production inventory: 234 operations, 3 public, 231 authenticated, identical under `python -O`. |
| ENG-02 | `48cc11ead7a6438e6c14015889d2653c4e450349` | Neon PASS WITH NOTES, `neon-batch08-security-qa`, on tree `909477f4`. `nginx -t` and a 19-path header and cache probe showed no behavioural difference between nginx 1.30.6 and 1.30.7. |
| PORTABLE-COMPOSE-001 | `0626b2385ef13a310ab7cf3a7d9465f2212af012` | Neon PASS, `neon-batch08-security-qa`, on tree `5f84ef31`. It contains both ENG-02 commits. A live `PYTHONOPTIMIZE=1` portable smoke on the locally merged nginx 1.30.7 tree passed, and a wrong-head negative control failed closed. |

The source merges conflict only in the additive `docs/progress.md` log, which preparation
resolves by keeping both sides. Every other changed file equals its source tip. The sources'
file sets are disjoint from the changes on `main` since their base `fdc75e8`.

`eng-02-source.md` records its standalone measurements on nginx 1.30.6. The reviewer's
1.30.6/1.30.7 comparison is the evidence for the integrated base. The two-theme browser CSP
sweep ran on standalone `b31048d`. It must be repeated on the release-candidate images,
together with Batch 07 protected media and downloads.

Reviewer notes recorded as follow-ups, none blocking:

- `backend/pyproject.toml` mypy `files` does not include `backend/scripts/check_api_routes.py`
  and its test. They pass when checked explicitly.
- `test_production_route_inventory_satisfies_gsec_allowlist` passes ambient `FLORABASE_*`
  variables to its subprocess.
- `backend/scripts/check_api_routes.py` and its test are unclassified in
  `scripts/verification-impact.json`, so changes to them escalate to FULL.
- `scripts/smoke-beta-images.py` and `scripts/smoke-beta-runtime.py` keep a few
  out-of-scope `assert` statements.

The exact-commit independent review and a fresh canonical FULL run on the exact candidate.
The proposed release class of ENG-03 is `best-effort` (in `scope-v1.json`) and awaits the
operator's decision. The eight release-candidate blockers and RC-SEQ-01 remain open. G-SEC
acceptance remains pending.
