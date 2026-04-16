# Context Index

This folder is the navigation layer for durable project context. Read this file
first, then follow the topic links that match the task.

## Recommended Reading Order

1. [`../AGENTS.md`](../AGENTS.md) - repo rules, constraints, terminology, and
   documentation discipline
2. [`implementation.md`](implementation.md) - current phase status and tracker
3. [`product_overview.md`](product_overview.md) - product goals, glossary, and
   non-goals
4. [`architecture.md`](architecture.md) - system boundaries and high-level flow
5. Topic docs for the task at hand

## File Map

- [`implementation.md`](implementation.md) - phase tracker and dated
  implementation notes
- [`product_overview.md`](product_overview.md) - product intent, supported
  outcomes, canonical terms, and non-goals
- [`architecture.md`](architecture.md) - runtime shape, storage boundaries, and
  subsystem map
- [`repo_structure.md`](repo_structure.md) - current repo layout, ownership, and
  placement rules
- [`backend.md`](backend.md) - backend direction, service boundaries, and what
  not to introduce early
- [`frontend.md`](frontend.md) - server-rendered UI direction, template rules,
  and no-JS boundaries
- [`database.md`](database.md) - conceptual persistence direction and table
  responsibilities
- [`media_pipeline.md`](media_pipeline.md) - local media lifecycle and storage
  expectations
- [`platform_registry.md`](platform_registry.md) - configured-platform
  visibility and capability direction
- [`posting_workflow.md`](posting_workflow.md) - intended publishing flow from
  draft to per-platform logging
- [`roadmap.md`](roadmap.md) - high-level narrative of the phased delivery plan
- [`changelog.md`](changelog.md) - human-readable notable repo changes

## Decision Log

- [`decisions/001_local_first_architecture.md`](decisions/001_local_first_architecture.md)
  - local-only runtime and storage model
- [`decisions/002_fastapi_jinja_choice.md`](decisions/002_fastapi_jinja_choice.md)
  - FastAPI + Jinja2 application stack
- [`decisions/003_sqlite_sqlalchemy_choice.md`](decisions/003_sqlite_sqlalchemy_choice.md)
  - SQLite + SQLAlchemy + Alembic persistence direction
- [`decisions/004_no_js_frontend_choice.md`](decisions/004_no_js_frontend_choice.md)
  - no JavaScript frontend rule
- [`decisions/005_master_post_media_items_post_logs.md`](decisions/005_master_post_media_items_post_logs.md)
  - core data model direction
- [`decisions/006_carousel_first_class_support.md`](decisions/006_carousel_first_class_support.md)
  - ordered carousel support as a first-class concept
- [`decisions/007_preview_artifacts_are_regenerable_local_derivatives.md`](decisions/007_preview_artifacts_are_regenerable_local_derivatives.md)
  - generated preview files as local regenerable derivatives

## Task Routing

- DB work: read [`database.md`](database.md),
  [`architecture.md`](architecture.md),
  [`decisions/003_sqlite_sqlalchemy_choice.md`](decisions/003_sqlite_sqlalchemy_choice.md),
  and
  [`decisions/005_master_post_media_items_post_logs.md`](decisions/005_master_post_media_items_post_logs.md)
- Frontend work: read [`frontend.md`](frontend.md),
  [`architecture.md`](architecture.md), and
  [`repo_structure.md`](repo_structure.md)
- Media work: read [`media_pipeline.md`](media_pipeline.md),
  [`database.md`](database.md), and
  [`decisions/006_carousel_first_class_support.md`](decisions/006_carousel_first_class_support.md)
- Config or platform visibility work: read [`backend.md`](backend.md) and
  [`platform_registry.md`](platform_registry.md)
- Posting workflow work: read [`posting_workflow.md`](posting_workflow.md),
  [`platform_registry.md`](platform_registry.md), and
  [`database.md`](database.md)
- Repo organization or documentation work: read
  [`repo_structure.md`](repo_structure.md),
  [`roadmap.md`](roadmap.md), and [`changelog.md`](changelog.md)

## Maintenance Rule

Whenever a structural change lands, update the matching topic doc, then update
[`implementation.md`](implementation.md) if the change affects phase status or
phase completion notes.
