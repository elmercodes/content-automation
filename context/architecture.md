# Architecture

The application is a local-only Python web app. FastAPI handles HTTP requests,
Jinja2 renders HTML, SQLite stores durable records, and the filesystem under
`storage/` holds local media and generated artifacts.

## Current Baseline

- `app/main.py` creates the FastAPI app and ensures local storage paths exist at
  startup.
- `app/config.py` owns `.env` loading and repo-stable local path resolution.
- `app/accounts_service.py` owns local connected-account persistence, OAuth
  state records, and provider runtime status evaluation.
- `app/oauth_clients.py` owns provider-specific OAuth authorization, token
  exchange, account lookup, and token refresh behavior.
- `app/compose_service.py`, `app/platform_selection_service.py`,
  `app/preview_service.py`, `app/posting_service.py`, and
  `app/history_service.py` still own the server-rendered posting workflow.
- `app/platforms/registry.py` owns static provider metadata: app-level config
  requirements, OAuth scopes, preview rules, and coarse posting capabilities.
- `app/platforms/adapters.py` and `app/platforms/x_adapter.py` own the posting
  adapter contract and the real X posting integration.
- `app/db/` owns SQLAlchemy models and runtime DB helpers.
- `app/web/routes/` owns server-rendered pages for home, accounts, compose,
  review, results, and history.

## Runtime Boundaries

- Browser: standard HTML navigation and form submission only
- Settings layer: app-level runtime config and provider app config from `.env`
- Connected-account layer: OAuth connection attempts, connected account state,
  token refresh, and provider readiness
- Platform registry: code-owned provider metadata and capability rules
- Workflow services: compose, selection, preview, submission, and history
- Adapter layer: provider-specific posting APIs behind a small contract
- SQLite: durable app state including connected accounts and post logs
- Local filesystem: uploads, generated media, and the SQLite file itself

## Intended Flow

1. The user configures provider app credentials in `.env`.
2. The user connects provider accounts from the server-rendered `Accounts` page.
3. OAuth callbacks store provider-authorized tokens locally in SQLite.
4. The compose, platform-selection, preview, and final-review flow only exposes
   providers that have an active connected account.
5. Posting adapters consume the stored connected-account tokens instead of any
   env-provided user credentials.
6. Results and history render from saved posts, media items, connected-account
   snapshots, and post platform logs.

## Structural Rules

- Keep the architecture local-first and single-machine by default.
- Keep `.env` limited to app-level runtime and provider app configuration.
- Keep user/provider account authorization in OAuth flows plus local DB storage.
- Do not introduce a JS frontend, remote worker system, or cloud control plane.

## Related Docs

- [`backend.md`](backend.md) for backend ownership
- [`database.md`](database.md) for persistence shape
- [`platform_registry.md`](platform_registry.md) for provider availability rules
- [`posting_workflow.md`](posting_workflow.md) for workflow sequencing
