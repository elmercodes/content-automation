# Frontend Direction

The frontend is server-rendered HTML delivered by FastAPI and Jinja2. The user
experience should come from clear page flow, forms, and templates rather than a
JavaScript application shell.

## Current Baseline

- Shared layout in `app/templates/base.html`
- Shared partials in `app/templates/partials/`
- Workflow pages in `app/templates/pages/`
- Static styling in `app/static/styles.css`
- A real multipart compose form now lives on `pages/compose.html`
- A real configured-platform selection form now lives on `pages/platforms.html`
- A real one-platform-at-a-time preview step now lives on
  `pages/review_platforms.html`
- The platform review step now renders ordered server-generated preview items
  for image carousels without client-side interactivity
- The final review step now preserves selected-platform workflow context on
  `pages/review_final.html`

## Direction

- Keep templates organized by page and partial responsibility.
- Prefer normal links, form posts, redirects, and rendered responses.
- Keep pages readable without client-side scripting.
- Favor accessible HTML semantics and explicit server-side validation messages.

## Template Rules

- Use Jinja2 for layout composition and repeated fragments.
- Keep a shared page shell for nav and workflow progress so later pages reuse a
  stable structure.
- Keep business logic out of templates.
- Pass already-prepared page state from route handlers into the template.
- Keep visual state understandable from rendered HTML alone.
- When form validation fails, preserve text inputs and render explicit error
  messages in HTML.
- Keep platform-selection state explicit in the URL handoff between steps rather
  than relying on hidden client-side state or JavaScript.
- Keep preview navigation explicit in the URL with `post_id`, repeated
  `platform_slug`, and a simple `platform_index` rather than client-side state.
- Treat the preview UI as a practical local mock, not a pixel-perfect clone of
  provider interfaces.
- Prefer simple ordered lists, thumbnail-like frames, and explicit item counts
  for carousel review instead of interactive gallery controls.

## No-JS Boundary

- Do not introduce a JavaScript frontend framework.
- Do not depend on client-side state to make page flow work.
- Do not move validation or platform-selection rules into browser code.
- Keep file-selection expectations honest: browsers will require media files to
  be selected again after a validation failure.
- Keep safe empty states honest. If a workflow step is opened without the
  required `post_id` or selected platforms, render an explanatory HTML state
  instead of simulating fake progress.
- Keep preview rendering backend-owned. Generated preview images should be
  requested from a backend route, not by mounting the storage directory as a
  public static tree.

## Related Docs

- [`architecture.md`](architecture.md) for request flow
- [`repo_structure.md`](repo_structure.md) for template and static asset
  placement
- [`decisions/004_no_js_frontend_choice.md`](decisions/004_no_js_frontend_choice.md)
  for the explicit decision record
