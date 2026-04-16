# ADR 004: No JavaScript Frontend

- Status: Accepted
- Date: 2026-04-15

## Decision

Keep the user interface server-rendered and avoid a JavaScript frontend
framework.

## Rationale

- The product is intentionally simple and local-first.
- Server-rendered templates are sufficient for the planned workflow.
- Avoiding a frontend framework keeps the repo smaller and easier for agents to
  reason about.

## Alternatives Not Chosen

- React or other SPA frontend
- Hybrid UI that depends on client-side state for basic page flow

## Consequences

- Forms, redirects, and rendered templates remain the primary interaction model.
- Validation and platform-selection logic stay on the backend.
- Any future JavaScript use would need an explicit product decision, not a
  casual convenience change.
