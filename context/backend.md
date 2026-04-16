# Backend Direction

The backend remains the source of truth for page flow, validation, and local
orchestration. It should grow from the current FastAPI baseline without turning
into an API-first or cloud-oriented system.

## Current Baseline

- FastAPI app factory in `app/main.py`
- Local settings in `app/config.py`
- Platform registry in `app/platforms/registry.py`
- Router entrypoint in `app/web/router.py`
- Route modules under `app/web/routes/`
- Alembic scaffold without active models

## Direction

- Keep request handling server-rendered and HTML-first.
- Use backend code to decide which platforms are visible, which validations run,
  and what is persisted locally.
- Add domain or service modules only when later phases introduce real workflow
  complexity. Do not create empty package trees before they carry real logic.
- Keep platform integrations behind clear backend boundaries instead of leaking
  provider logic into templates.

## Boundaries

- Settings: load from `.env` and local defaults only
- Platform registry: expose configured-platform visibility and coarse capability
  metadata to the web layer
- Web layer: translate HTTP requests into domain actions and rendered responses
- Domain logic: validate posts, media items, and platform eligibility
- Persistence layer: store master posts, media items, and post platform logs
- Adapter layer: defer until the posting phase and keep provider specifics out
  of core workflow code

## Avoid Early

- Separate frontend/backoffice apps
- Client-side UI orchestration
- Remote APIs that mirror server-rendered page behavior
- Background job frameworks or worker processes

## Related Docs

- [`architecture.md`](architecture.md) for overall boundaries
- [`platform_registry.md`](platform_registry.md) for configured-platform logic
- [`posting_workflow.md`](posting_workflow.md) for the intended flow
