# Changelog

Notable repository changes are listed here in a short human-readable form.

## 2026-04-16

- Completed Phase 4 with the first SQLAlchemy models for master posts, ordered
  media items, and post platform logs.
- Wired Alembic to the app metadata, added the first migration revision, and
  documented the local migration workflow.
- Added SQLite runtime session helpers, DB-focused automated tests, and updated
  repo docs for the new persistence baseline.

## 2026-04-15

- Completed Phase 3 with a modular server-rendered app skeleton, centralized
  settings/path handling, a platform registry foundation, and placeholder
  workflow pages.
- Completed Phase 2 documentation expansion with topic docs, ADRs, a real
  context index, and stronger agent guidance.
- Documented the durable product, architecture, backend, frontend, database,
  media, platform registry, and posting workflow direction.
- Completed Phase 1 foundation with the FastAPI/Jinja2 smoke app, local storage
  conventions, Alembic scaffold, and initial repo guidance.

## Entry Style

- Keep entries short and user-readable.
- Prefer grouped changes over file-by-file inventories.
- Record notable shifts in product direction, architecture, or workflow.
