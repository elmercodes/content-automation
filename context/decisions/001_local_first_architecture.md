# ADR 001: Local-First Architecture

- Status: Accepted
- Date: 2026-04-15

## Decision

Build the application as a local-only system that runs on the user's machine and
stores its state locally.

## Rationale

- The product goal is simple publishing from a local workstation.
- Local storage reduces operational complexity and setup cost.
- The repo is explicitly avoiding cloud control planes and hosted dependencies.

## Alternatives Not Chosen

- Hosted backend with remote storage
- Hybrid local app with required cloud synchronization

## Consequences

- SQLite and local filesystem storage are first-class parts of the design.
- Credentials remain in local `.env` files.
- Features that assume remote workers, multi-user coordination, or cloud
  persistence are out of scope unless product direction changes.
