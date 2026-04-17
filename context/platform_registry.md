# Platform Registry

The application should present only platforms that are configured locally. The
platform registry is the backend-owned source of truth for visibility,
capability rules, and credential expectations.

## Direction

- Drive platform visibility from local configuration, not hard-coded UI lists.
- Keep credential lookup in `.env`.
- Centralize platform capabilities so validation and UI decisions share the same
  source of truth.

## Phase 9 Baseline

- The registry lives in `app/platforms/registry.py`.
- The supported platform set currently includes `instagram`, `facebook`, and
  `x` because those are the only local credential hints documented in
  `.env.example`.
- Registry entries hold:
  - stable slug and display name
  - required settings fields for local visibility
  - posting-spec metadata that separates direct submission support from simple
    configured visibility, including whether direct posting is enabled, whether
    single-image or image-carousel posting is supported, provider posting
    credential requirements, and operator-facing notes
  - coarse capability metadata such as carousel support, maximum carousel size,
    single-media allowed media types, carousel-allowed media types, and broad
    caption limits
  - preview canvas metadata for the review step, including a fixed
    canvas size, frame label, and deterministic background color
  - lightweight validation notes that can be shown in server-rendered workflow
    pages
- `configured` means the platform is visible in the local UI because its
  required setting fields are present in `.env`.
- `posting ready` means a provider adapter can attempt submission for that
  platform after shared validation and provider-specific credential checks.
- Phase 6 uses the registry for the first real workflow decision: the
  platform-selection page shows only configured platforms and then applies
  post-specific eligibility guardrails in backend service code before a
  platform can be selected.
- Phase 7 reuses the same registry entries to decide how preview generation and
  text-limit visibility should behave per selected platform, and Phase 8 uses
  the same metadata to decide carousel eligibility.

## Supported vs Configured vs Eligible

- `supported in code`: present in `PLATFORM_REGISTRY`
- `configured locally`: required settings are present in `.env`
- `eligible for the workflow step`: configured and not blocked by the current
  master post or its media items

## Registry Responsibilities

- Determine whether a platform is configured locally.
- Expose platform display metadata for server-rendered pages.
- Expose capability metadata such as supported post types or media constraints.
- Expose preview metadata so normalization and review UI use the same backend
  source of truth.
- Give the posting workflow a stable place to resolve platform-specific rules.

## Boundaries

- The registry is a backend concern, not a template concern.
- Post-specific eligibility checks belong in workflow service code, not in the
  registry itself.
- Preview file generation belongs in workflow service and normalization modules,
  not in the registry itself.
- Provider-specific HTTP logic belongs in adapter modules, not in the registry.
- The registry should expose posting capability and credential expectations,
  but it should not build request payloads or perform network calls.
- The current workflow remains image-only even where a future platform adapter
  may support video outside this phase.

## Related Docs

- [`backend.md`](backend.md) for backend ownership
- [`posting_workflow.md`](posting_workflow.md) for when registry data is used
- [`product_overview.md`](product_overview.md) for the rule that only configured
  platforms are shown
