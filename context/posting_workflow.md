# Posting Workflow

This file describes the intended publishing sequence at a workflow level. It is
not an implementation spec for provider adapters yet.

## Intended Flow

1. Create or load a master post.
2. Attach one or more ordered media items.
3. Determine which platforms are configured locally.
4. Let the user choose from those configured platforms only.
5. Validate the master post and media items against platform constraints.
6. Submit to each selected platform through backend adapters in a controlled
   way.
7. Record per-platform outcomes in post platform logs.

## Safety Expectations

- Validate before submission, not after.
- Isolate per-platform outcomes so one failure does not erase other results.
- Keep enough local history to understand what was attempted and what happened.

## Deferred Details

- Actual adapter implementations
- Retry policy and submission concurrency policy
- Final result and history page design
- Preview generation and media normalization mechanics

## Related Docs

- [`product_overview.md`](product_overview.md) for supported outcomes
- [`database.md`](database.md) for persistent records
- [`platform_registry.md`](platform_registry.md) for configured-platform rules
