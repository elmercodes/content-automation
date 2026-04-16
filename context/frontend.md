# Frontend Direction

The frontend is server-rendered HTML delivered by FastAPI and Jinja2. The user
experience should come from clear page flow, forms, and templates rather than a
JavaScript application shell.

## Current Baseline

- Shared layout in `app/templates/base.html`
- Phase 1 homepage in `app/templates/pages/index.html`
- Static styling in `app/static/styles.css`

## Direction

- Keep templates organized by page and partial responsibility.
- Prefer normal links, form posts, redirects, and rendered responses.
- Keep pages readable without client-side scripting.
- Favor accessible HTML semantics and explicit server-side validation messages.

## Template Rules

- Use Jinja2 for layout composition and repeated fragments.
- Keep business logic out of templates.
- Pass already-prepared page state from route handlers into the template.
- Keep visual state understandable from rendered HTML alone.

## No-JS Boundary

- Do not introduce a JavaScript frontend framework.
- Do not depend on client-side state to make page flow work.
- Do not move validation or platform-selection rules into browser code.

## Related Docs

- [`architecture.md`](architecture.md) for request flow
- [`repo_structure.md`](repo_structure.md) for template and static asset
  placement
- [`decisions/004_no_js_frontend_choice.md`](decisions/004_no_js_frontend_choice.md)
  for the explicit decision record
