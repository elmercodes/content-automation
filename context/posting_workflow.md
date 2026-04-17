# Posting Workflow

This file describes the current publishing sequence at a workflow level.

## Current Flow

1. Create a master post through the compose flow.
2. Attach one or more ordered media items.
3. Connect provider accounts from the Accounts page as needed.
4. Open `Platforms` and choose from connected providers that are eligible for
   the current master post.
5. Review one selected platform at a time with generated local previews.
6. Open `Final review` and inspect posting readiness.
7. Submit selected platforms synchronously.
8. Record one `post_platform_logs` row per attempt, including the connected
   account snapshot used for that attempt.
9. Review immediate results and later history pages.

## Runtime Notes

- Platform selection is now gated by connected accounts, not env tokens.
- Final review can surface `not_connected` or `reauthorization_required` if an
  account changes state after selection.
- X posts through stored connected-account tokens.
- Instagram and Facebook remain explicit unsupported outcomes for direct
  posting, even when connected.

## Related Docs

- [`platform_registry.md`](platform_registry.md)
- [`database.md`](database.md)
- [`architecture.md`](architecture.md)
