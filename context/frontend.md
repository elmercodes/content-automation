# Frontend Direction

The frontend stays server-rendered with FastAPI + Jinja2. OAuth account
connection also stays HTML-first and no-JS.

## Current Baseline

- Shared layout in `app/templates/base.html`
- Workflow pages under `app/templates/pages/`
- A new `Accounts` page for provider connection management
- A no-JS Facebook Page selection page for multi-Page logins
- Existing compose, platforms, preview, final review, results, and history
  pages remain server-rendered

## Rules

- Use normal links, forms, redirects, and rendered responses.
- Do not introduce client-side state to make OAuth or workflow routing work.
- Keep provider selection explicit in URLs and forms.
- Keep account-connection state understandable from rendered HTML alone.

## Related Docs

- [`architecture.md`](architecture.md)
- [`repo_structure.md`](repo_structure.md)
- [`decisions/004_no_js_frontend_choice.md`](decisions/004_no_js_frontend_choice.md)
