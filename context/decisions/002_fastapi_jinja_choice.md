# ADR 002: FastAPI + Jinja2

- Status: Accepted
- Date: 2026-04-15

## Decision

Use FastAPI for the Python web backend and Jinja2 for server-rendered HTML.

## Rationale

- The app needs a lightweight Python web stack, not a separate frontend
  framework.
- FastAPI gives a clean app structure and startup lifecycle.
- Jinja2 supports the no-JS, server-rendered workflow directly.

## Alternatives Not Chosen

- Django full-stack framework
- Flask with ad hoc structure
- Separate frontend framework paired with a JSON API

## Consequences

- Route handlers remain responsible for preparing rendered page state.
- Templates stay HTML-first and thin.
- The UI should evolve through server-rendered page flow rather than a client
  application.
