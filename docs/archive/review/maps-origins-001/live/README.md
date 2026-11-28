# Authenticated Collection origins Feature Review

2026-10-22. Live URL: <http://localhost:15174/#/map>.
Source: `/home/alessandro/.codex/worktrees/c902/florabase`,
branch `feat/maps-origins-001-candidate`, HEAD
`b3f1de4693f50a12396344d251a16a0b4ded4b92`, including the unstaged/untracked
Origins candidate. This evidence supersedes only the earlier live-environment
availability limitation. Operator product acceptance and independent QA remain pending.

## Authorized replacement and identity

Read-only `make workflow-resources` and `make feature-review-status` first confirmed
that the old Review belonged to delivered `b139`. Its frontend/backend were stopped,
PostgreSQL was healthy at `20261013_0042`, and all three owned volumes remained.
The operator then explicitly approved deletion. Only after that approval, the owning
`b139` guarded `feature-review-stop` and
`feature-review-remove CONFIRM_REMOVE_REVIEW=florabase-feature-review` removed its
Review containers/network and the exact Review database/media/dependency volumes.
No worktree or other environment was deleted.

`make feature-review-up` from `c902` initialized new Review-owned resources and
migrated the fresh isolated database. The owner was bootstrapped using the existing
application CLI with password stdin. A cryptographically random password was kept
in a mode-0600 user-owned local file outside the repository; no password, hash,
session cookie or CSRF value is stored in this evidence. Login is `owner`.
The guarded `make feature-review-seed` initialized fixture **v4 / ready / 80 records**.

[Final guarded environment status](environment-status.txt) confirms all three services
healthy, source `c902`, launched HEAD `b3f1de4`, and code/database revision
`20261013_0042`. An additional narrow owner read returned one enabled owner named
`owner`. Login through the real browser form and authenticated session API also
confirmed the owner. Ordinary auth sessions were created; no collection rows or
fixture records were changed for screenshots.

DEV, UAT, Stable Preview, Sourcing Preview, production and unrelated worktrees were
preserved. A final guarded inventory retained their original sources, containers
and volumes; only Review's source changed to `c902`.

## Browser verification

These captures use the actual Review frontend, backend, authentication and persisted
synthetic fixture. There are **no intercepted API responses or mocked tiles** in this
run. The separate earlier screenshots remain explicitly frontend-only fixture evidence.
The final online check observed **12 loaded basemap images, zero failed/pending**.
The online switch was subsequently disabled through the UI for local-context/pane checks.
New visits retain the product's ordinary online-basemap default.

| Evidence | Purpose |
| --- | --- |
| [Online desktop](desktop-online.png) | Actual OSM tiles and synthetic recorded site |
| [Desktop inspector](desktop-inspector.png) | Exact WGS84 pair, unknown accuracy, direct SeedLot, identity and management navigation |
| [1440 map](1440-map.png), [inspector](1440-inspector.png) | Desktop composition |
| [1024 map](1024-map.png), [inspector](1024-inspector.png) | Tablet pane switch |
| [390 map](390-map.png), [inspector](390-inspector.png) | Mobile pane switch and wrapped content |

[Browser report](browser-report.json) records completed assertions and measurements:

- Real UI sign-in as `owner`, corroborated by authenticated API session.
- All four KPI values match the authoritative map response; three breakdown dialogs work.
- Real Leaflet Enter selection and textual keyboard/pointer selection synchronize marker
  state, exact-coordinate inspector, unknown accuracy and Geography management route.
- Identity search matches the recorded label. No-match search clears selected details;
  clearing filters does not resurrect inspection. Excluding SeedLots produces the exact
  remaining eligible-record count, then removing that filter restores the standard view.
- 1440×844, 1024×844 and 390×844 real browser interactions have no horizontal overflow.
  Map DOM and selection survive responsive switching; the revealed map has positive size.
- No runtime page errors occurred.

| Viewport | Map CSS size | Map vertical range | Document width / height |
| --- | --- | --- | --- |
| 1440×844 | 787.59×430.44 | 270.95–701.39 | 1440 / 844 |
| 1024×844 | 726×430.44 | 392.95–823.39 | 1024 / 924 |
| 390×844 | 356×320.72 | 564.17–884.89 | 390 / 1094 |

## Coverage limits

The standard fixture contains **one mapped site, one directly linked SeedLot, one
botanical identity, zero sites missing coordinates and unknown accuracy**. It does
not demonstrate multiple origins, coincident sites, directly linked Plants/PlantGroups
or a positive accuracy circle in this live database. Those behaviors retain the earlier
labelled renderer/screen fixtures and automated evidence; no records were added merely
to manufacture richer live screenshots. No external occurrence evidence was loaded.

True browser zoom, an actual screen-reader session, physical touch and large-collection
performance remain operator checks. The low-detail local overview is intentionally
coarse at the single-site fit zoom. Online provider success is one observed check,
not a future availability guarantee.

No canonical verification, staging, commit, push, PR, delivery or DEV upgrade was run.
Review remains running for the operator. The app browser URL was requested to open;
the operator can also use the URL directly and sign in with the supplied local credentials.

**ORIGINS_LIVE_REVIEW_READY**
