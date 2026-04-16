# Database Direction

The repo is moving toward a small local SQLite schema managed with SQLAlchemy
and Alembic. Phase 2 documents the intended record model without locking every
column or migration detail yet.

## Current Baseline

- SQLite is already the configured database target.
- Alembic is scaffolded through `alembic/`.
- No SQLAlchemy models or metadata are wired into migrations yet.

## Conceptual Records

- `posts`: stores each master post and the shared content needed to publish it
- `media_items`: stores ordered media attached to a master post
- `post_platform_logs`: stores per-platform submission records and outcomes

## Relationship Direction

- One master post can have one or more media items.
- Media items keep an explicit order so carousel behavior is durable.
- One master post can have one or more post platform logs over time.
- Post platform logs should capture enough information to explain what happened
  for each platform attempt.

## Boundaries

- SQLite remains the only supported database engine.
- SQLAlchemy should own model definitions once Phase 4 begins.
- Alembic should own schema migration history.
- Exact columns, indexes, and enum strategy remain Phase 4 work.

## Related Docs

- [`product_overview.md`](product_overview.md) for terminology
- [`media_pipeline.md`](media_pipeline.md) for media lifecycle expectations
- [`decisions/003_sqlite_sqlalchemy_choice.md`](decisions/003_sqlite_sqlalchemy_choice.md)
  and
  [`decisions/005_master_post_media_items_post_logs.md`](decisions/005_master_post_media_items_post_logs.md)
  for the durable decisions
