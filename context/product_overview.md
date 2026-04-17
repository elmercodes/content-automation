# Product Overview

This application is a local-first social media publisher. It helps a user
prepare a master post, attach media items, connect provider accounts through
OAuth, validate platform constraints, submit where supported, and keep a local
history.

## Product Goals

- Keep the full workflow on the user's machine.
- Support server-rendered compose, review, and submission pages.
- Gate provider availability on locally stored connected accounts.
- Record enough local history to understand what was attempted and what
  happened.

## Non-Goals

- Hosted multi-user collaboration
- A JavaScript frontend or SPA shell
- Remote token storage
- Background scheduling or queue infrastructure

## Related Docs

- [`architecture.md`](architecture.md)
- [`database.md`](database.md)
- [`posting_workflow.md`](posting_workflow.md)
