# Release tooling for v1.0.0

The supported sequence is `v0.1.0-beta.N` → `v1.0.0-rc.N` → `v1.0.0`. Beta and
RC releases are GitHub prereleases. Stable uses the same protected workflow and immutable
assets. Each application image is promoted under its exact version tag. Portable Compose
selects all three images by digest and explicitly targets `linux/amd64`. PostgreSQL retains its
independent version and pinned index and platform digests.

## Prepare and rehearse

1. In an isolated checkout, set the same version without the leading `v` in
   `release/inputs.json`, `backend/pyproject.toml`, `backend/src/florabase/__init__.py`,
   `frontend/package.json` and every `ARG VERSION` default in both Dockerfiles.
2. Run `make api-generate`, check the generated artifacts, and commit the synchronized version locally.
3. From the clean commit on native Linux amd64 with the workflow-pinned Docker Buildx, run
   `make release-preflight-local`. The command prints the directory holding the log, release
   assets, image smoke output, security reports and proposed publication request. It uses only
   disposable local registries to write and test images. The generated Compose file refers to that
   run's local registry. The protected workflow renders the public asset from the same template
   with GHCR digest references.
4. Compare `output/assets/release-manifest.json`, `output/assets/portable-compose.yaml`,
   `output/diagnostics/image-smoke.log` and `output/diagnostics/publication-state.json`.
   The package, module, label, Compose header and manifest versions should agree. Python package
   metadata uses its normalized spelling, such as `1.0.0rc1` for `1.0.0-rc.1`.
   The intended Git tag adds the leading `v`.

## DOC-02 interface and publication prerequisites

DOC-02 owns `scripts/check-features.py` and the release-scope data. REL-01 calls
`scripts/check-features.py --release-candidate` for v1 hosted rehearsal and protected publication.
The release tooling first confirms that the checker advertises this flag, then requires it to pass.
The checker rejects unsupported arguments and exits nonzero while any `certify` or
`release-work` feature remains `planned` or `in_progress`. Beta follows its existing path.
Artifact-only local rehearsal can run while release-scope certification is still open.

An operator cutting a release needs the candidate on protected `main`, exact-SHA successful
`quality`, `integration`, `build`, `release-migration` and hosted `rehearse` jobs, the approved
version tag at that SHA, and the existing protected `beta-release` environment approval for that
same SHA. The workflow requires unused application version identities, validates the image scans
and smokes before promotion, then requires provenance for the exact images and assets before
publishing. Complete the [release scope gates](scope-v1.md#release-gates) for REL-03, including the
RC soak before stable.
