# Changelog

Notable changes to Florabase, newest first. Versions follow the
[versioning policy](docs/versioning.md). The engineering record of every increment is
[docs/progress.md](docs/progress.md); this file lists what an operator of an installation needs
to know.

## Unreleased

Changes on `main` since `v0.1.0-beta.5`. They ship in the next prerelease. The source is versioned
`0.1.0-beta.6`, which is not tagged or published.

### Added

- Portable Docker Compose distribution: a three-service `portable-compose.yaml` release asset with
  explicit schema initialization, upgrade, paired backup and isolated restore (#161). See the
  [installation guide](docs/portable-installation.md).
- Owner password change in Settings → Account, and an offline password reset command for the
  portable installation (#179).
- Cuttings: vegetative material lots and rooting attempts. Delivered and still being finished
  for v1.0.0 (#167).
- Material ancestry explorer, phenology observations in the Journal, operator-managed botanical
  synonyms and installation as a web app (#167).
- Accepted-name correction with retained name history (#165).
- Plant height measurements with correction history (#163).
- Explicit date choice for Journal entries: Today, Another date or Date unknown; and a work-first
  Today page (#177).
- A collection onboarding guide and CSV templates for a first import (#159).

### Changed

- Date fields never fill in a missing year, month or day; an incomplete date must be completed
  or cleared before saving (#177).
- WCVP v16 is the default source for native-range enrichment; v15 stays available (#174).
- The reviewed WGSRPD crosswalk covers more regions (#175).
- Backend and frontend dependency updates (#169, #171).

### Upgrade notes

- The database schema head moves from `20261013_0042` to `20261110_0047`. Apply it with the
  explicit upgrade command of your installation path after a paired backup; the application
  never migrates at startup.
- Installations from the `v0.1.0-beta.5` controller bundle upgrade with the controller's
  documented upgrade, or move to the portable stack through a paired backup and the
  [isolated restore](docs/portable-installation.md#isolated-restore) procedure.

## v0.1.0-beta.5 — 2026-11-08

Prerelease of the private beta series. The only prerelease with a published GitHub Release:
controller bundle (`compose.yaml`, `florabasectl.py`, `florabase.env.example`), release
manifest, release notes, source archive, PostgreSQL SBOM and digest-pinned linux/amd64 images.

- Recovered the release pipeline after the beta.4 publication attempt (#158).

## v0.1.0-beta.4 — 2026-11-08

Tagged; no GitHub Release is published for it.

- The distribution is rehearsed before publication (#155).
- Consolidated beta installation guidance (#156).

## v0.1.0-beta.3 — 2026-11-07

Tagged; no GitHub Release is published for it.

- Registry preflight reads GHCR manifests directly (#154).

## v0.1.0-beta.2 — 2026-11-07

Tagged; no GitHub Release is published for it.

- Completed the hashed lock of the release tools (#152).

## v0.1.0-beta.1 — 2026-11-07

Tagged; no GitHub Release is published for it. First beta tag of the single-owner application:
botanical identities and profiles, suppliers, orders, locations, seed lots, sowings, plants and
plant groups, Journal and History, Schedule, harvests and stored material, media, maps, taxonomy,
search, saved views, bulk moves, labels and CSV import/export, with the controller-based
image distribution.
