# Posting Workflow

This file describes the intended publishing sequence at a workflow level. It is
not an implementation spec for provider adapters yet.

## Intended Flow

1. Create a master post through the compose flow.
2. Attach one or more ordered media items during local upload intake.
3. Redirect the saved master post into the platforms page.
4. Determine which platforms are configured locally and currently eligible.
5. Let the user choose from those configured platforms only.
6. Hand the selected platforms into the platform review step.
7. Validate the master post and media items against platform constraints.
8. Submit to each selected platform through backend adapters in a controlled
   way.
9. Record per-platform outcomes in post platform logs.

## Phase 6 Baseline

- `POST /compose` creates a master post and ordered media items locally.
- The compose flow accepts optional caption and hashtag text plus one or more
  image uploads.
- Successful compose submissions redirect to `/platforms?post_id=<id>`.
- `GET /platforms?post_id=<id>` resolves configured platforms from the backend
  platform registry and applies lightweight eligibility guardrails based on the
  saved master post and media items.
- `POST /platforms` accepts one or more selected platforms and redirects to
  `/review/platforms?post_id=<id>&platform_slug=...`.
- Failed compose or platform-selection submissions return to the same
  server-rendered page with explicit HTML error messages and no partial local
  state retained.

## Safety Expectations

- Validate before submission, not after.
- Isolate per-platform outcomes so one failure does not erase other results.
- Keep enough local history to understand what was attempted and what happened.

## Deferred Details

- Actual adapter implementations
- Durable platform selection persistence
- Retry policy and submission concurrency policy
- Final result and history page design
- Preview generation and media normalization mechanics

## Related Docs

- [`product_overview.md`](product_overview.md) for supported outcomes
- [`database.md`](database.md) for persistent records
- [`platform_registry.md`](platform_registry.md) for configured-platform rules
