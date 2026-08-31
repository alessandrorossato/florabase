# ADR 0003: REST with backend-owned OpenAPI

Status: accepted

## Decision

Expose versioned REST endpoints under `/api/v1`. FastAPI-generated OpenAPI is authoritative; committed TypeScript declarations are generated from a committed OpenAPI artifact and checked for drift.

## Consequences

The API contract has one source. Updating endpoints may require regenerating client types. GraphQL and manually duplicated request/response interfaces are out of scope.
