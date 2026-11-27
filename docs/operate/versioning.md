# Versioning and compatibility

> Summary: Beta, release-candidate, and v1.x versioning, compatibility, and upgrade policy.

This page states how Florabase releases are numbered and what a 1.x release promises. The
[v1.0.0 release scope](../release/scope-v1.md) is authoritative; where this page and the scope
disagree, the scope applies.

## Release line

| Stage | Version | Tag | Meaning |
| --- | --- | --- | --- |
| Private beta | `0.1.0-beta.N` | `v0.1.0-beta.N` | Prereleases for the operator's own use. No compatibility promise. |
| Release candidate | `1.0.0-rc.N` | `v1.0.0-rc.N` | A candidate for v1.0.0, evaluated against the release gates and run for the soak period. |
| Stable | `1.0.0` | `v1.0.0` | The first public stable release. |

There is no public 0.1 stable release between the beta series and the release candidates. `N`
starts at 1 and increases by one. A tag is the version prefixed with `v`. Every version surface
of one release (package versions, image labels, `/release.json`, the release manifest and the
tag) carries the same version. The [release tooling](../release/rel-01-tooling.md) checks this
for beta, release candidates and stable releases. Hosted v1 rehearsal and protected v1
publication also require the release-scope checker to pass. Python package metadata shows
the PEP 440 normalised form (for example `1.0.0rc1`). The source text and every other surface
use `1.0.0-rc.1`.

Beta and release-candidate publications are GitHub prereleases; stable publication uses the
protected release workflow. A tag alone does not establish that a GitHub Release was published.
[CHANGELOG.md](../../CHANGELOG.md) distinguishes planned, tagged and published versions.

## What 1.x promises

From 1.0.0 onward, within the 1.x series:

- **Database upgrades.** A database created by any 1.x release can be upgraded forward by the
  documented procedure in the [installation guide](installation.md#upgrade).
- **Backups.** A paired database and media backup made by the documented procedure can be
  restored by it.
- **CSV.** The documented [CSV import and export](../features/tools/import-export.md) columns keep their meaning.

## What 1.x does not promise

- **The HTTP API.** `/api/v1` is the application's own boundary between its frontend and
  backend. It may change in any release, and outside clients are not supported.
- **In-place downgrades.** The documented installation procedures never migrate a database
  backwards. Returning to an earlier release means restoring the paired backup taken before
  the upgrade, with the earlier release's images, into fresh paths.
- **Other installations.** Only the release `compose.yaml` on linux/amd64 is certified. Building
  from source is for development. The controller bundle was withdrawn by
  [ADR 0008](../decisions/0008-self-initializing-single-compose.md).
- **Betas.** They carry none of the promises above. The upgrade path that v1.0.0 certifies
  from the beta series is the one recorded by its release gates (G-MIGRATE, G-UPGRADE).
- Multi-user use, offline use and architectures other than linux/amd64.

## Supported versions

Security fixes and corrections are made on `main` and released in the next version. Once
v1.0.0 exists, the latest 1.x release is the supported version; earlier releases, betas and
release candidates are not patched. See the [security policy](../../SECURITY.md).
