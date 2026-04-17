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
- `app/platform_selection_service.py` owns configured-platform resolution,
  lightweight eligibility checks, and the platform-review workflow handoff.
- `app/preview_service.py` owns preview-state assembly, text-length
  visibility, and warning generation for the review step.
- `app/posting_service.py` owns final-review posting readiness, synchronous
  per-platform submission orchestration, and post platform log persistence.
- `app/history_service.py` owns read-side results and history state assembly on
  top of saved posts, media items, and post platform logs.
- `app/presentation.py` owns small backend-owned display helpers such as
  human-readable UTC timestamps for results and history pages.
- `app/image_normalization.py` owns deterministic image normalization and
  generated preview file creation under local storage.
- `app/db/` owns the SQLite local database models, engine/session helpers, and
  persistence metadata.
- `app/platforms/registry.py` is the backend-owned platform registry for
  supported-platform metadata, configured-platform visibility, preview canvas
  metadata, and posting capability metadata.
- `app/platforms/adapters.py` and `app/platforms/x_adapter.py` own the small
  posting adapter contract, unsupported-adapter fallback, and the real X
  provider integration.
- `app/web/router.py` and `app/web/routes/` define the server-rendered route
  shell for home, compose, platform review, results, and history pages.
- `app/web/routes/media.py` serves generated preview files plus uploaded media
  originals through narrow backend-owned routes instead of exposing the full
  `storage/` tree.
- `app/templates/` now includes a shared base layout, workflow partials, and
  real preview, final-review, results, history index, history detail, and
  browser-friendly error pages for the server-rendered workflow.
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
- Preview engine: selected-platform preview assembly plus deterministic local
  warning state
- Image normalization: proportional resize onto platform-owned canvases without
  default cropping
- Workflow handoff: `post_id` plus repeated `platform_slug` query params between
  platform selection, platform review, and final review
- SQLite: durable app state
- Local filesystem: uploads, generated media, and the SQLite file itself
- Generated preview route: backend-owned file serving for preview artifacts
- Uploaded media route: backend-owned file serving for original local uploads
  reused in history views
- HTML error handling: browser-facing 404-style failures render through the same
  server-rendered page shell instead of falling back to JSON
- Posting adapter layer: per-platform runtime validation and provider HTTP
  submission behind a small backend-owned contract
- Submission orchestration: synchronous, sequential final-review posting with
  one durable post platform log per selected platform attempt
- History read side: newest-first post listing plus per-post outcome summaries
  built from saved media items and platform logs

## Intended Flow

1. The browser submits a request to the FastAPI app.
2. The backend loads settings, validates input, saves local uploads, resolves
   configured platforms, generates preview files when needed, and coordinates
   workflow logic.
3. Persistent data is stored in SQLite while uploaded originals and generated
   preview files remain on local disk.
4. The backend renders the next HTML response, serves generated preview media
   and uploaded originals through narrow routes, submits selected platforms
   synchronously when final review is posted, redirects with PRG into the saved
   results step, and exposes longer-lived history pages from SQLite-backed
   read-side state.

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
