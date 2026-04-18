# Platform Registry

The platform registry is the code-owned source of truth for supported
providers, app-level config requirements, OAuth scopes, preview rules, and
posting capabilities.

## Current Baseline

- The registry lives in `app/platforms/registry.py`.
- Supported providers are `instagram`, `facebook`, and `x`.
- Registry entries now define:
  - provider slug and display name
  - required app-level `.env` settings
  - requested OAuth scopes
  - preview canvas metadata
  - coarse media and carousel rules
  - direct-posting capability metadata

## State Definitions

- `supported in code`: present in `PLATFORM_REGISTRY`
- `app configured`: required provider app settings exist in `.env`
- `connectable`: app configured and the app can start an OAuth flow
- `connected`: an active connected account exists in SQLite
- `ready to post`: connected, required posting scopes are present, and direct
  posting is enabled in code

## Current Posting Capabilities

- `x`: direct posting is enabled for single images and image carousels up to 4
  items.
- `facebook`: direct posting is enabled for one local image per submission and
  requires the `pages_manage_posts` scope on the connected Page token.
- `instagram`: direct posting remains disabled because Meta content publishing
  requires publicly reachable media URLs, which the local-only workflow does
  not provide.

## Boundaries

- The registry is static metadata only.
- Connected-account state belongs in `app/accounts_service.py`, not in the
  registry.
- Provider HTTP and OAuth details belong in `app/oauth_clients.py` and adapter
  modules, not in the registry.

## Related Docs

- [`backend.md`](backend.md)
- [`posting_workflow.md`](posting_workflow.md)
- [`architecture.md`](architecture.md)
