# Architecture

The application is a local-only Python web app. FastAPI handles HTTP requests,
Jinja2 renders HTML, SQLite stores durable records, and the filesystem under
`storage/` holds local media and generated artifacts.

## Current Baseline

- `app/main.py` creates the FastAPI app and ensures local storage paths exist at
  startup.
- `app/config.py` owns the settings layer, `.env` loading, and repo-stable
  local path resolution.
- `app/compose_service.py` orchestrates master post creation and attach-one-or-
  more media item persistence for the compose flow.
- `app/media_uploads.py` owns local upload validation, file saves, metadata
  extraction, and cleanup on failed compose attempts.
- `app/db/` owns the SQLite local database models, engine/session helpers, and
  persistence metadata.
- `app/platforms/registry.py` is the backend-owned platform registry for
  supported-platform metadata and configured-platform visibility.
- `app/web/router.py` and `app/web/routes/` define the server-rendered route
  shell for home, compose, platform review, results, and history pages.
- `app/templates/` now includes a shared base layout, workflow partials, and
  placeholder pages for the future publishing flow.
- `alembic/` owns the migration layer and is wired to the SQLAlchemy metadata.

## Runtime Boundaries

- Browser: standard HTML form submission and navigation only
- FastAPI app: routing, request handling, response rendering, and startup
  lifecycle
- Settings layer: local configuration, `.env` loading, and local path
  conventions
- Migration layer: explicit schema history and local DB upgrades through
  Alembic
- Platform registry: supported-platform metadata and configured-platform
  visibility
- SQLite: durable app state
- Local filesystem: uploads, generated media, and the SQLite file itself
- Platform adapters: deferred until later phases

## Intended Flow

1. The browser submits a request to the FastAPI app.
2. The backend loads settings, validates input, saves local uploads, and
   coordinates workflow logic.
3. Persistent data is stored in SQLite and media files remain on local disk.
4. The backend renders the next HTML response or returns a simple status
   payload.

## Structural Rules

- Keep the architecture local-first and single-machine by default.
- Prefer clear server-side boundaries over early abstraction.
- Do not make JSON APIs the primary UI contract.
- Do not add remote worker, queue, or scheduler infrastructure.

## Related Docs

- [`backend.md`](backend.md) describes backend direction.
- [`frontend.md`](frontend.md) defines the no-JS UI model.
- [`media_pipeline.md`](media_pipeline.md) explains local media handling.
- [`decisions/001_local_first_architecture.md`](decisions/001_local_first_architecture.md)
  records the local-first choice.
