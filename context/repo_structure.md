# Repo Structure

This repo is intentionally small. Keep the layout obvious and avoid adding new
top-level directories without a clear reason.

## Current Layout

- `app/` - application package
- `app/web/` - web routes and template-facing request handlers
- `app/templates/` - Jinja2 templates
- `app/static/` - CSS and other static assets
- `alembic/` - migration scaffold and future migration revisions
- `context/` - durable project and agent documentation
- `storage/` - local runtime data root for uploads, generated assets, and the
  SQLite database
- `tests/` - automated tests

## Placement Rules

- Put request handlers and page flow code under `app/web/`.
- Keep configuration and settings logic near `app/config.py` unless growth makes
  a dedicated settings module necessary.
- Add future persistence modules under `app/` rather than creating a separate
  service repository or package tree.
- Keep repo-facing guidance in `AGENTS.md` and topic-specific guidance under
  `context/`.

## Storage Conventions

- `storage/uploads/` is for user-provided media.
- `storage/generated/` is for local derivatives, previews, or normalized assets.
- `storage/db/` is for the local SQLite database file.
- Runtime data under `storage/` stays out of version control except for
  placeholder `.gitkeep` files.

## Documentation Ownership

- `AGENTS.md` owns repo-wide working rules.
- `context/index.md` owns documentation navigation.
- Topic docs under `context/` own durable design intent for their area.
- `context/implementation.md` owns phase status only.
