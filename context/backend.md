# Backend Direction

The backend remains the source of truth for page flow, validation, and local
orchestration. It should grow from the current FastAPI baseline without turning
into an API-first or cloud-oriented system.

## Current Baseline

- FastAPI app factory in `app/main.py`
- Local settings in `app/config.py`
- Compose flow orchestration in `app/compose_service.py`
- Local upload and image metadata helpers in `app/media_uploads.py`
- Platform selection orchestration in `app/platform_selection_service.py`
- Preview-state orchestration in `app/preview_service.py`
- Posting orchestration in `app/posting_service.py`
- Read-side results/history state assembly in `app/history_service.py`
- Deterministic image normalization in `app/image_normalization.py`
- SQLite persistence helpers and ORM models in `app/db/`
- Platform registry in `app/platforms/registry.py`
- Posting adapter contract in `app/platforms/adapters.py`
- Real X posting adapter in `app/platforms/x_adapter.py`
- Router entrypoint in `app/web/router.py`
- Route modules under `app/web/routes/`
- Generated-preview and uploaded-media serving routes in
  `app/web/routes/media.py`
- Alembic migration layer with active schema revisions for the current workflow

## Direction

- Keep request handling server-rendered and HTML-first.
- Use backend code to decide which platforms are visible, which validations run,
  and what is persisted locally.
- Keep upload handling and media metadata extraction in backend modules instead
  of pushing file logic into routes or templates.
- Add domain or service modules only when later phases introduce real workflow
  complexity. Phases 7 and 9 now justify dedicated preview, normalization, and
  posting orchestration modules, but the repo should still avoid empty package
  trees.
- Keep platform integrations behind clear backend boundaries instead of leaking
  provider logic into templates.

## Boundaries

- Settings: load from `.env` and local defaults only
- Compose flow: normalize form input, validate basic upload rules, and create
  master posts plus media items locally
- Platform selection flow: load one saved master post, resolve configured and
  eligible platforms, validate selected platforms, and hand the workflow into
  platform review
- Preview engine: build one selected-platform review state at a time, combine
  caption plus hashtags for length visibility, and surface obvious warning
  states from registry metadata
- Posting service: reload reviewed posts, derive per-platform posting requests,
  perform shared pre-submit validation, submit each platform sequentially, and
  persist normalized outcomes
- History service: load newest-first master post summaries, derive latest
  platform outcomes per post, and assemble post-detail ledger views from saved
  media items plus post platform logs
- Image normalization: preserve uploaded originals, generate derived preview
  images under `storage/generated/`, and avoid default cropping
- Persistence runtime: obtain synchronous SQLAlchemy sessions from `app/db/`
  and keep SQLite access backend-owned
- Platform registry: expose configured-platform visibility and coarse capability
  metadata plus preview canvas metadata to the web layer
- Web layer: translate HTTP requests into domain actions and rendered responses
- Domain logic: validate posts, media items, and platform eligibility
- Persistence layer: store master posts, media items, and post platform logs
- Generated media route: serve only preview artifacts rooted under
  `settings.generated_path`
- Uploaded media route: serve only saved uploads rooted under
  `settings.uploads_path` so history pages can render local thumbnails without
  mounting all of `storage/`
- Adapter layer: keep provider-specific HTTP details and runtime validation out
  of core workflow orchestration

## Avoid Early

- Separate frontend/backoffice apps
- Client-side UI orchestration
- Remote APIs that mirror server-rendered page behavior
- Background job frameworks or worker processes

## Related Docs

- [`architecture.md`](architecture.md) for overall boundaries
- [`platform_registry.md`](platform_registry.md) for configured-platform logic
- [`posting_workflow.md`](posting_workflow.md) for the intended flow
