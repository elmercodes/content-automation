# Platform Registry

The application should present only platforms that are configured locally. A
platform registry will eventually provide the backend with a single source of
truth for visibility, capability rules, and credential expectations.

## Direction

- Drive platform visibility from local configuration, not hard-coded UI lists.
- Keep credential lookup in `.env`.
- Centralize platform capabilities so validation and UI decisions share the same
  source of truth.

## Phase 3 Baseline

- The registry lives in `app/platforms/registry.py`.
- Phase 3 currently includes `instagram`, `facebook`, and `x` as supported
  platform slugs because those are the only local credential hints documented in
  `.env.example`.
- Registry entries currently hold:
  - stable slug and display name
  - required settings fields for local visibility
  - coarse capability metadata such as carousel support, maximum carousel size,
    allowed media types, and broad caption limits
  - lightweight validation notes for placeholder UI display
- Phase 3 "configured" means the platform is visible in the local UI because
  its required setting fields are present. It does not yet mean the future
  adapter contract is complete.

## Registry Responsibilities

- Determine whether a platform is configured locally.
- Expose platform display metadata for server-rendered pages.
- Expose capability metadata such as supported post types or media constraints.
- Give the posting workflow a stable place to resolve platform-specific rules.

## Boundaries

- The registry is a backend concern, not a template concern.
- Provider-specific HTTP logic is deferred until the adapter phase.
- Exact adapter credential rules, submission payload details, and final
  validation behavior are deferred until later phases.

## Related Docs

- [`backend.md`](backend.md) for backend ownership
- [`posting_workflow.md`](posting_workflow.md) for when registry data is used
- [`product_overview.md`](product_overview.md) for the rule that only configured
  platforms are shown
