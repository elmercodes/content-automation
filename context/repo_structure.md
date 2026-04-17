# Repo Structure

This repo stays intentionally small. Keep the layout obvious.

## Current Layout

- `app/accounts_service.py` - connected-account persistence and runtime state
- `app/oauth_clients.py` - provider-specific OAuth connect and refresh helpers
- `app/platforms/` - provider metadata and posting adapters
- `app/db/` - SQLAlchemy models and runtime DB helpers
- `app/web/routes/accounts.py` - server-rendered account connection workflow
- `app/web/routes/workflow.py` - compose, review, results, and history flow
- `app/templates/pages/` - server-rendered page templates
- `alembic/` - migration revisions
- `context/` - durable project and agent docs
- `storage/` - local runtime data root
- `tests/` - automated tests

## Placement Rules

- Put provider OAuth HTTP details in `app/oauth_clients.py`.
- Put shared connected-account orchestration in `app/accounts_service.py`.
- Keep provider posting HTTP logic in `app/platforms/`.
- Keep server-rendered route handlers in `app/web/routes/`.

## Related Docs

- [`architecture.md`](architecture.md)
- [`backend.md`](backend.md)
