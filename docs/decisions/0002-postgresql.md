# ADR 0002: PostgreSQL as source of truth

Status: accepted

## Decision

Use PostgreSQL 18 as the relational source of truth. Apply every schema change through Alembic and persist database files in a named Compose volume.

## Consequences

Development and production share database behavior and constraints. Operators must manage volume durability, upgrades, and backups. SQLite is not a production substitute and tests requiring PostgreSQL must be identified as integration tests.
