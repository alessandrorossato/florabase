# GLOBAL-VISUAL-001 visual evidence

- [Pre-change inventory](audit.md): every primary route and important Collection detail/form was
  audited against preserved synthetic UAT before production edits.
- `before/`: original live UAT, delivered owner `4ff7`, revision 0042, fixture v4/66.
- `global-navigation/sign-in.jpg`: actual candidate sign-in through the real unauthenticated API
  response; no authentication response was simulated.
- `layout-fixtures/`: **static React DOM exported from isolated repository test fixtures**, rendered
  with the candidate's real styles and self-hosted fonts. These images assess typography, surfaces,
  form/control sizing, header wrapping and available-space behavior. They are not live authenticated
  UAT interaction evidence. Data differs from UAT and a first-captured directory may intentionally
  show an empty/source-error state. Native dialog behavior is verified by tests separately.

The temporary DOM recorder and static server live under `/tmp`, do not modify production code and
have no backend, login or authentication service. `screenshots.json` records exact image pixel sizes; some provider captures differ from requested
viewport dimensions. `layout-fixtures/viewport-evidence.json` records DOM width probes for three
representative layouts at requested widths 390/820/1024/1440/1920, with no horizontal overflow.
Screenshot metadata distinguishes viewport-size probes from true browser zoom. Resizing is never represented as zoom. The operator has now completed the authenticated Feature Review walkthrough and accepted the reviewed GLOBAL-VISUAL-001 scope. Actual 125%/150% tab-zoom checks could not be automated in the available browser surface; viewport proxies remain labelled and this limitation is retained in the final handoff. User authorization and the preserved frontend restoration baseline are recorded in the handoff. No simulated CSRF success, origin rewrite or shared frontend replacement ran.

- `frontend-tests.json`: 666 passing tests across 64 files on the prior frozen candidate, plus the
  final 7-test Taxonomy rerun; exact source fingerprints and scope are recorded.
- `bundle-impact.json`: baseline and final candidate production assets with the same dependencies.
- `token-contrast.json`: 9 passing semantic pairs, with explicitly limited accessibility scope.

Operator visual acceptance is complete. Independent review found no material blocker. The canonical
FULL gate passed on the candidate tree: backend 939 unit tests, frontend 707 tests in 66 files,
PostgreSQL integration 735 tests, environment workflow 33 tests, Review fixture guards 20 passed with
one expected live-probe skip, generated API check, lint/type/format checks, production backend and
frontend builds, and migration cycle. Actual tab-zoom automation was unavailable; no viewport proxy
is described as browser zoom.
