# Database Direction

The application uses a small local SQLite schema managed through SQLAlchemy and
Alembic. The schema now covers both publishing workflow data and connected
account state.

## Current Baseline

- `posts`: the master post record
- `media_items`: ordered media attached to one master post
- `post_platform_logs`: one durable per-platform attempt/outcome record plus the
  connected-account snapshot used for that attempt
- `connected_accounts`: one locally stored connected account per provider
- `oauth_connection_attempts`: short-lived local OAuth state and PKCE storage

## Connected-Account Rules

- `connected_accounts.provider_slug` is unique.
- Tokens, scopes, expiry timestamps, and provider metadata stay in SQLite on the
  local machine.
- `connection_status` distinguishes active, disconnected, and
  reauthorization-required states.
- Disconnects clear local tokens without deleting history.

## Post Log Rules

- `post_platform_logs.status` now supports OAuth-era states including
  `not_connected` and `reauthorization_required`.
- Each log can store `account_display_name` and `account_identifier` so history
  remains readable after reconnects.

## Runtime Rules

- SQLite remains the only supported database engine.
- SQLAlchemy sessions are synchronous and backend-owned.
- Schema changes go through Alembic revisions only.
- App startup upgrades the configured local SQLite database to the latest
  Alembic revision before serving requests.

## Related Docs

- [`architecture.md`](architecture.md)
- [`posting_workflow.md`](posting_workflow.md)
- [`decisions/003_sqlite_sqlalchemy_choice.md`](decisions/003_sqlite_sqlalchemy_choice.md)
- [`decisions/005_master_post_media_items_post_logs.md`](decisions/005_master_post_media_items_post_logs.md)
