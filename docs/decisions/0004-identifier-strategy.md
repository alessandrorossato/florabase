# ADR 0004: UUIDv7 identifiers

Status: accepted

## Decision

Future domain entities will use UUIDv7 identifiers generated in application code with Python's standard `uuid.uuid7()` before insertion. PostgreSQL stores them as native `uuid` values.

## Consequences

Identifiers are globally unique, sortable by creation time for index locality, available before flush, and avoid leaking sequential row counts. UUID timestamps are metadata, not authoritative creation timestamps; entities still need explicit UTC timestamps. The first scaffold migration has no domain identifiers.
