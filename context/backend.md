# Backend Direction

The backend remains the source of truth for page flow, validation, OAuth
orchestration, and local persistence. The app stays server-rendered and
local-only.

## Current Baseline

- `app/config.py` loads local runtime settings and provider app config from
  `.env`.
- `app/accounts_service.py` owns connected-account persistence, OAuth attempt
  records, disconnects, and runtime status evaluation.
- `app/oauth_clients.py` owns provider-specific OAuth redirects, token
  exchange, Page selection support, and X token refresh.
- `app/platform_selection_service.py` resolves connected platforms for the
  workflow instead of env-visible platforms.
- `app/posting_service.py` builds posting requests from saved master posts plus
  stored connected-account tokens.
- `app/platforms/x_adapter.py` posts using OAuth-derived tokens from SQLite, not
  env credentials.
- `app/web/routes/accounts.py` owns the server-rendered account connection
  workflow.

## Boundaries

- Settings: app-level runtime config and provider app config only
- Connected accounts: DB-backed local user authorization state
- Registry: provider metadata and capability rules, not live account state
- Workflow services: post/media validation and page-state assembly
- Adapters: provider-specific HTTP details
- Web layer: HTML forms, redirects, and rendered responses

## Avoid Early

- Client-side OAuth orchestration
- Background refresh jobs
- Remote token storage
- Hosted account-management control planes

## Related Docs

- [`architecture.md`](architecture.md)
- [`database.md`](database.md)
- [`platform_registry.md`](platform_registry.md)
