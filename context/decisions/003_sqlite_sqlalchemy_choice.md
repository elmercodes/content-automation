# ADR 003: SQLite + SQLAlchemy + Alembic

- Status: Accepted
- Date: 2026-04-15

## Decision

Use local SQLite for persistence, SQLAlchemy for model definitions, and Alembic
for schema migrations.

## Rationale

- SQLite fits the local-first single-machine deployment model.
- SQLAlchemy provides durable model definitions without forcing a remote DB.
- Alembic keeps schema evolution explicit and reviewable.

## Alternatives Not Chosen

- Hosted PostgreSQL or other remote database services
- Raw SQL-only schema management
- ORM-free persistence without migration tooling

## Consequences

- The database file lives under `storage/db/`.
- Later schema changes should land through Alembic revisions.
- Design choices should assume SQLite constraints unless the product direction
  changes.
