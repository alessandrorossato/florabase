# DEV reference indexes

DEV discovers the following files in the primary checkout's ignored `backend/src/.source-cache/`.
The existing source bind exposes that directory as `/app/src/.source-cache/`. Reference files
are kept outside Git, the backend image, and the PostgreSQL and media volumes.

| Reference | Cache file | DEV path setting |
| --- | --- | --- |
| WFO 2026-06 | `wfo-2026-06.sqlite`, with sibling `wfo-2026-06.sha256` | `FLORABASE_WFO_SNAPSHOT_PATH` |
| Kew WCVP v16 | `wcvp-v16/index.sqlite`, with sibling `wcvp-v16/index.sha256` | `FLORABASE_WCVP_V16_SNAPSHOT_PATH` |
| Kew WCVP v15, optional | `wcvp-v15.sqlite` | `FLORABASE_WCVP_SNAPSHOT_PATH` |

Use the defaults or put absolute **container** paths within `/app/src/.source-cache/` in the
primary `.env`. An unset or empty value selects the default. For v16, use a dedicated child
directory of the cache. Keep this directory writable only by the operator. Local seals establish
integrity within that trusted cache. Obtain indexes through Florabase's approved archive builders.

Development overlays resolve the paths within their own source bind. A linked UAT worktree
has its own cache and database. Production uses the baseline Compose file and has no DEV
reference settings or source bind. Startup never provisions indexes. The app stays healthy with
missing files, and source-dependent requests report unavailability. The DEV backend also
reports v16 unavailable if its local seal is missing or fails checksum validation.
Native-range review opens on v15. Select **16** explicitly to use the installed v16 source.

## Activate after merge

From the clean, updated primary `main` checkout, run:

```sh
make dev-references-status
make dev-references-setup
make dev-references-verify
make dev-up
make dev-status
```

To reuse a bundle provisioned in a feature worktree, copy it before setup. Set
`FEATURE_CACHE` to that worktree's absolute `backend/src/.source-cache` path. With
the default DEV paths and the WFO cache already present, run from primary `main`:

```sh
destination=backend/src/.source-cache/wcvp-v16
if [ ! -e "$destination" ] && [ ! -L "$destination" ]; then
  cp -aT -- "$FEATURE_CACHE/wcvp-v16" "$destination"
fi
```

If an earlier checkout still owns DEV, use the documented `make dev-stop` recovery command
before `make dev-up`. No Golden init/reset or database upgrade is needed for this change.

Setup verifies the previously installed WFO file against the approved index digest
`ac49e6348c71810a3f90ff5ba40e390faf95a6835155c13e80c79a8cc0528126` and the sibling seal.
The reviewed artifact is 413,069,312 bytes, built from archive SHA-256
`75f1ad1f371978c9e46f3044152c07ed276fe57be9fb9a15b3621b19cf231987`. If setup reports
the file or seal missing, restore the reviewed pair from a trusted copy to the configured
cache path. The command does not download WFO.

Setup uses the approved WCVP v16 builder with the official Kew URL and exact archive
SHA-256 `d32ea2b3a85e489b14e83bcc9eae7274532e1d113753f7be290d4b2dfde573fa`. The URL can
rotate. If Kew serves different bytes, setup stops. To use an already retrieved copy of the
same official archive, place it in the ignored cache and supply its actual retrieval time:

```sh
make dev-references-setup WCVP_ARCHIVE=wcvp-v16.zip WCVP_RETRIEVED_AT='<actual ISO-8601 timestamp with offset>'
```

Allow at least 3 GiB free for the v16 build. The builder checks the release, archive hash,
members and source schema. Setup checks the produced SQLite schema, integrity, full row
counts and an accepted-name search before publishing the index and seal together. Setup
reuses a valid sealed bundle. A pre-existing directory with an absent or invalid index is
preserved for inspection. Status only reports file presence. Verify checks both required
sources and also validates the optional v15 file if installed. Use the v15 builder described in
[WCVP-VERSION-001](wcvp-version-001.md) if historical source lookup is needed.

These commands run one-shot in the worktree's Quality project with no database dependency.
They operate on the source cache only. DEV restarts, Golden reset and normal updates to
primary `main` preserve the ignored cache. Back up the cache separately if it needs to survive
replacement of the checkout.

## Golden taxonomy

COMPREHENSIVE Golden DEV represents 92 botanical identities. Its nine WFO links record
synthetic fixture evidence. Eight disagree with real WFO placement and one is intentionally
stale. With WFO 2026-06 all 92 currently appear unresolved. The new configuration makes real
sources searchable. Golden taxonomy placement still needs the real-source extension below.

## Follow-up handoffs

### WCVP-DEFAULT-001

Switch the API and UI default together to version 16 once DEV has the full 1,448,984-taxon,
1,995,338-distribution index. Make missing v16 explicit and retain version 15 as an explicit
historical selection. Existing v15 links, proposals and applied evidence keep their original
source, link UUID and crosswalk. Any change of release requires separate confirmation with
the selected version's exact ID and evidence. Existing native ranges stay in place unless the
operator uses an existing explicit write action. Test v16-only, both installed and missing v16,
plus v15 historical inspection and Apply with the v15 snapshot absent. Regenerate and check
the API artifacts when the default changes.

### BOTANICAL-MATCH-001

Generate deterministic suggestions from WFO 2026-06 and WCVP v16, and from existing GBIF
or CoL XR lookups where Florabase can retrieve exact provider records. Retain each provider,
release, source record and accepted-target ID, authorship, rank and match reason. Resolve
synonyms through that same release's documented accepted relationship. Surface homonyms,
conflicting placements, authorship/rank differences and missing evidence for manual
resolution. Fuzzy suggestions require review, as do all links for real collections. Confirmation
uses the existing provider-specific write path. Keep local identities separate and treat provider
IDs independently.

For Golden DEV, define an opt-in versioned fixture extension with exact artifact fingerprints
and reviewed per-identity assertions. Confirm only unique exact accepted matches with
compatible authorship and rank, including a recorded synonym route where applicable.
Stage the extension through the Golden generator and verification workflow with its own
manifest and digest. Preserve the original COMPREHENSIVE profile and its reset path.
Review reproducibility and stale, ambiguous and unavailable source cases before enabling
the extension.
