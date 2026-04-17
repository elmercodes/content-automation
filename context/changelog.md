# Changelog

Notable repository changes are listed here in a short human-readable form.

## 2026-04-17

- Completed Phase 11 with final shareability polish: stronger onboarding docs,
  clearer `.env.example` guidance, browser-friendly HTML error pages, cleaned up
  user-facing copy, and shared test helpers for the main workflow suite.
- Added setup/runtime coverage for storage initialization and configuration
  surface accuracy, plus browser-facing coverage for the new HTML not-found
  state.
- Completed Phase 10 with a real local history ledger: newest-first history
  index, per-post detail pages, shared results/history outcome presentation,
  and safe uploaded-media rendering through backend-owned routes.
- Split read-side results and history state assembly into `app/history_service.py`
  so posting orchestration stays focused on submission and log persistence.
- Added automated coverage for history queries, history/detail page rendering,
  results-to-history navigation, and safe uploaded-media serving.
- Completed Phase 9 with synchronous final-review submission, a real X posting
  adapter, explicit unsupported outcomes for deferred providers, and a real
  results page backed by post platform logs.
- Added a small adapter contract, normalized post platform log statuses plus
  response summaries, and automated coverage for submission success, failure
  isolation, duplicate blocking, and results rendering.
- Completed Phase 8 with ordered multi-image carousel review support in the
  server-rendered workflow.
- Extended backend platform capability metadata for carousel-specific image
  rules and tightened platform eligibility messaging for unsupported or
  over-limit carousel selections.
- Updated the review step to generate and render one local preview artifact per
  ordered media item while preserving the existing no-JS page flow.
- Added automated coverage for carousel preview generation, review rendering,
  and carousel platform eligibility limits.

## 2026-04-16

- Completed Phase 7 with deterministic image normalization, generated preview
  files under local storage, and a real platform review step.
- Added preview-state and generated-media backend modules, platform-owned
  preview canvas metadata, and server-rendered one-platform-at-a-time review
  navigation.
- Added automated tests for preview generation, warning states, generated-media
  routing, and the updated review workflow.
- Completed Phase 6 with a real configured-platform selection step, lightweight
  eligibility guardrails, and a URL-based handoff into platform review.
- Added backend platform-selection helpers, server-rendered selection and
  review states, and tests covering configured-platform visibility plus
  validation.
- Completed Phase 5 with a real compose form, local image upload intake,
  ordered media item persistence, and handoff into the platforms page.
- Added backend compose and upload helpers, server-rendered validation states,
  and tests covering successful uploads plus cleanup on failed submissions.
- Completed Phase 4 with the first SQLAlchemy models for master posts, ordered
  media items, and post platform logs.
- Wired Alembic to the app metadata, added the first migration revision, and
  documented the local migration workflow.
- Added SQLite runtime session helpers, DB-focused automated tests, and updated
  repo docs for the new persistence baseline.

## 2026-04-15

- Completed Phase 3 with a modular server-rendered app skeleton, centralized
  settings/path handling, a platform registry foundation, and placeholder
  workflow pages.
- Completed Phase 2 documentation expansion with topic docs, ADRs, a real
  context index, and stronger agent guidance.
- Documented the durable product, architecture, backend, frontend, database,
  media, platform registry, and posting workflow direction.
- Completed Phase 1 foundation with the FastAPI/Jinja2 smoke app, local storage
  conventions, Alembic scaffold, and initial repo guidance.

## Entry Style

- Keep entries short and user-readable.
- Prefer grouped changes over file-by-file inventories.
- Record notable shifts in product direction, architecture, or workflow.
