# Posting Workflow

This file describes the current publishing sequence at a workflow level,
including the Phase 9 submission handoff and the Phase 10 read-side history
views.

## Intended Flow

1. Create a master post through the compose flow.
2. Attach one or more ordered media items during local upload intake.
3. Redirect the saved master post into the platforms page.
4. Determine which platforms are configured locally and currently eligible.
5. Let the user choose from those configured platforms only.
6. Hand the selected platforms into the platform review step.
7. Generate platform-aware previews, normalize image media for review, and show
   obvious warning states before submission exists.
8. Carry the selected-platform handoff into the final review checkpoint.
9. Validate the master post and media items against platform constraints before
   submission.
10. Submit to each selected platform through backend adapters in a controlled
   way.
11. Record per-platform outcomes in post platform logs.
12. Redirect into immediate results for the just-submitted post.
13. Expose longer-lived history pages that read saved posts, ordered media, and
    platform outcomes from SQLite.

## Current Baseline

- `POST /compose` creates a master post and ordered media items locally.
- The compose flow accepts optional caption and hashtag text plus one or more
  image uploads.
- Successful compose submissions redirect to `/platforms?post_id=<id>`.
- `GET /platforms?post_id=<id>` resolves configured platforms from the backend
  platform registry and applies lightweight eligibility guardrails based on the
  saved master post and media items.
- `POST /platforms` accepts one or more selected platforms and redirects to
  `/review/platforms?post_id=<id>&platform_slug=...`.
- `GET /review/platforms` now generates a local preview for one selected
  platform at a time, using the backend platform registry plus image
  normalization to show ordered per-item preview output, text length
  visibility, and obvious warning states.
- `GET /review/final` preserves the selected-platform handoff after preview
  generation, summarizes whether the master post is a single image or image
  carousel, and shows per-platform posting readiness.
- `POST /review/final` revalidates the selected platforms, blocks duplicate
  reposts after a successful prior submission, submits selected platforms
  synchronously in validated order, and writes one post platform log per
  platform attempt.
- `GET /results?post_id=<id>&platform_slug=...` now loads the latest saved post
  platform logs for the just-submitted master post, renders the normalized
  outcomes, and links into permanent history pages.
- `GET /history` now renders a newest-first local ledger of saved master posts,
  including unsubmitted posts and each post's latest platform outcomes.
- `GET /history/<post_id>` now renders one saved master post in detail,
  including full caption/hashtags, ordered attached media, latest per-platform
  outcomes, and full attempt history from post platform logs.
- Phase 9 includes one real adapter: X posting for single-image and image-only
  multi-image submissions. Instagram and Facebook currently normalize to
  explicit unsupported outcomes instead of crashing the batch.
- Failed compose or platform-selection submissions return to the same
  server-rendered page with explicit HTML error messages and no partial local
  state retained.

## Safety Expectations

- Validate before submission, not after.
- Isolate per-platform outcomes so one failure does not erase other results.
- Keep enough local history to understand what was attempted and what happened.
- Keep submission synchronous and sequential in the request-response cycle
  until a later phase justifies a different execution model.

## Deferred Details

- Durable platform selection persistence
- Retry policy beyond explicit user resubmission
- Search, filtering, or analytics on top of the saved history ledger

## Related Docs

- [`product_overview.md`](product_overview.md) for supported outcomes
- [`database.md`](database.md) for persistent records
- [`platform_registry.md`](platform_registry.md) for configured-platform rules
