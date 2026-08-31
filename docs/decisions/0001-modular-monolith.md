# ADR 0001: Modular monolith

Status: accepted

## Decision

Use one React frontend, one FastAPI backend, and one PostgreSQL database deployed together with Docker Compose. Keep backend modules organized by concrete capabilities as they appear.

## Consequences

Deployment, transactions, local development, and debugging stay simple. Feature modules may evolve internally without introducing network boundaries. New infrastructure requires a demonstrated need and a new decision.
