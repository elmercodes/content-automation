# Database Direction

The application now uses a small local SQLite schema managed through
SQLAlchemy models in `app/db/` and Alembic revisions under `alembic/versions/`.
The schema stays intentionally narrow: master posts, ordered media items, and
post platform logs.

## Current Baseline

- The SQLite local database URL comes from the settings layer in
  `app/config.py`.
- The default database file lives at `storage/db/app.db`.
- SQLAlchemy model metadata lives in `app/db/base.py` and `app/db/models.py`.
- Runtime engine and session helpers live in `app/db/session.py`.
- Alembic is wired to the app metadata and owns schema history from the first
  revision forward.

## Core Tables

- `posts`: the master post record with shared caption and hashtag text plus
  created and updated timestamps
- `media_items`: ordered assets attached to a master post with a durable
  `display_order` field, local file path reference, and lightweight media
  metadata
- `post_platform_logs`: per-platform operational records for submission intent
  or outcome, including platform slug, normalized status, optional external
  post ID, optional error details, and an optional compact response summary

## Relationship and Constraint Rules

- One master post can have many media items.
- One master post can have many post platform logs.
- `media_items.display_order` is first-class and unique per master post.
- `display_order` is zero-based and must be non-negative.
- `media_items.media_type` is limited to `image` or `video`.
- `post_platform_logs.status` is limited to `pending`, `posted`,
  `not_configured`, `unsupported`, `validation_failed`, or
  `submission_failed`.
- `platform_slug` stores the backend platform registry slug such as
  `instagram`, `facebook`, or `x`.
- `file_path` stores a path relative to the local `storage/` root rather than
  an absolute machine path.
- Phase 10 results and history views read the latest post platform log per
  platform plus the full attempt history for a post rather than introducing a
  second batch table.

## Runtime Rules

- SQLite remains the only supported database engine.
- SQLAlchemy sessions are synchronous and backend-owned.
- SQLite foreign-key enforcement is enabled at connection time.
- App startup creates the local storage directories, but schema creation and
  upgrades stay explicit through Alembic.

## Local Workflow

Apply the current schema before running the app on a clean checkout:

```bash
.venv/bin/alembic upgrade head
```

Create new schema changes through Alembic revisions instead of manual table
edits.

## Related Docs

- [`product_overview.md`](product_overview.md) for terminology
- [`architecture.md`](architecture.md) for runtime boundaries
- [`media_pipeline.md`](media_pipeline.md) for media lifecycle expectations
- [`decisions/003_sqlite_sqlalchemy_choice.md`](decisions/003_sqlite_sqlalchemy_choice.md)
  and
  [`decisions/005_master_post_media_items_post_logs.md`](decisions/005_master_post_media_items_post_logs.md)
  for the durable decisions
