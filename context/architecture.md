# Architecture

The application is a local-only Python web app. FastAPI handles HTTP requests,
Jinja2 renders HTML, SQLite stores durable records, and the filesystem under
`storage/` holds local media and generated artifacts.

## Current Baseline

- `app/main.py` creates the FastAPI app and ensures local storage paths exist at
  startup.
- `app/web/routes.py` contains a minimal server-rendered homepage and a health
  endpoint.
- Alembic is scaffolded, but no SQLAlchemy metadata is connected yet.

## Runtime Boundaries

- Browser: standard HTML form submission and navigation only
- FastAPI app: routing, request handling, response rendering, and startup
  lifecycle
- Settings layer: local configuration and `.env` loading
- SQLite: durable app state
- Local filesystem: uploads, generated media, and the SQLite file itself
- Platform adapters: deferred until later phases

## Intended Flow

1. The browser submits a request to the FastAPI app.
2. The backend loads settings, validates input, and coordinates domain logic.
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
