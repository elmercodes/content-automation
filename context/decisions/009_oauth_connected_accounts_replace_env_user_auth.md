# ADR 009: OAuth Connected Accounts Replace Env User Auth

- Status: Accepted
- Date: 2026-04-17

## Decision

Replace env-driven provider user auth with OAuth-based connected accounts stored
locally in SQLite. Keep `.env` only for app-level runtime settings and provider
app configuration.

## Rationale

- Provider availability should come from a user-connected account, not from
  hand-copied user tokens in `.env`.
- The app must stay local-first, server-rendered, and lightweight.
- Posting adapters need a stable way to consume stored user tokens that is
  separate from provider app registration data.

## Consequences

- The app now persists connected accounts and short-lived OAuth callback state.
- Platform selection and final-review readiness depend on connected-account
  state instead of env token presence.
- X posting uses stored OAuth-derived tokens.
- Facebook posting uses a stored Page token for direct single-image submission.
- Instagram can still be connected for workflow availability, but direct
  posting remains deferred because Meta requires a publicly reachable media URL.
