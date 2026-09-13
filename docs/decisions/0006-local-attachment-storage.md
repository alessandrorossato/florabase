# ADR 0006: Guarded local attachment storage

- Status: accepted
- Date: 2026-09-13

## Context

`ATTACHMENT-001` established that uploaded media belongs outside PostgreSQL in backend-controlled
durable storage, but its verified planning text did not choose the concrete formats, limits,
lifecycle, or complete-backup procedure needed by `ATTACHMENT-002`. This ADR records the later
operator-approved implementation contract; it does not claim these details existed in the earlier
planning increment.

## Decision

Version 1 accepts only still JPEG, PNG, and WebP images, normalized as `image/jpeg`, `image/png`, and
`image/webp`. Pillow fully decodes the signature-selected format and image structure. SVG, GIF,
HEIC/HEIF, AVIF, PDF, documents, audio, and video are rejected. Browser media claims and filename
extensions are never trusted as content proof.

The application streams in 1 MiB chunks and permits at most exactly 25 MiB (26,214,400 bytes) of
file content. The production frontend proxy permits a 32 MiB request body so multipart overhead can
reach that application-owned limit. Original filenames are bounded normalized display metadata
only. A separate server-generated UUIDv7-based key selects a sharded path beneath one configured
absolute trusted root.

PostgreSQL stores one narrow Attachment row: UUIDv7 ID, unique storage key, display filename,
validated media type, positive byte size, SHA-256 digest, `active` or `pending_delete` state, and UTC
creation time. It stores neither binary content nor target relationships. `ATTACHMENT-003` owns
collection photos, external references, captions, attribution, history, galleries, and optional
BotanicalIdentity reference/cover images.

Creation writes a generated temporary file beneath the trusted root, validates and hashes it, then
atomically renames it on the same filesystem before committing metadata. A failed validation removes
the temporary file; a failed database commit triggers best-effort removal of the newly placed file.
Success is returned only after both sides exist. A process crash between rename and commit can leave
an inaccessible orphan file, which is preferable to committed metadata pointing to missing content.

Deletion commits `active → pending_delete` before unlinking. Pending attachments are never served.
Only a successful or already-completed unlink permits metadata removal. Unlink failure retains the
pending row for a deterministic DELETE retry; an unexpectedly missing active file is reported and
requires that retry before metadata is removed.

The backend alone mounts the dedicated `attachment_data` volume at
`/var/lib/florabase/attachments`, owned by its existing UID/GID 10001 runtime account. Nginx never
mounts or exposes it. Operator-supplied bind mounts must provide compatible ownership and
permissions. A complete backup and restore always pairs the PostgreSQL dump with the attachment
archive while backend writes are stopped, then verifies stored sizes and SHA-256 digests.

## Consequences

The initial backend serves owner-protected content directly with private, no-store responses and
performs synchronous validation, which is adequate for the 25 MiB single-owner boundary. There is no object storage, public media directory,
deduplication, thumbnail worker, generic media framework, or distributed transaction. Operational
backup artifacts are coordinated but are not an atomic storage-engine snapshot; unsupported direct
database or volume writes remain outside the guarantee.
