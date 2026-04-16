# AGENTS.md

## Project Summary

This repository builds a local-first social media publishing application that
runs on the user's machine. The stack is intentionally simple: Python backend,
FastAPI, Jinja2 templates, SQLite, local filesystem storage, and no JavaScript
frontend.

## Hard Constraints

- Keep the application local-only.
- Keep the backend in Python.
- Keep the UI server-rendered with FastAPI + Jinja2.
- Do not introduce a JavaScript frontend, SPA shell, or client-side state
  layer without an explicit product change.
- Keep secrets in `.env`.
- Keep local media and generated artifacts under `storage/`.
- Treat carousel media as first-class ordered items.
- Keep the product lightweight: no cloud control plane, no scheduling system,
  and no deep analytics layer.

## Canonical Terms

- `master post`: the user-authored post record that anchors one publishing
  intent and maps to the future `posts` table.
- `media item`: an ordered uploaded or generated asset attached to a master
  post and mapped to the future `media_items` table.
- `post platform log`: a per-platform outcome record for a master post, mapped
  to the future `post_platform_logs` table.
- `local-only`: all app state, credentials, media, and execution stay on the
  user's machine.
- `server-rendered workflow`: page navigation and form handling happen through
  backend-rendered HTML responses.
- `no-JS frontend`: HTML-first browser workflow with server-rendered templates
  and standard browser behavior only.

## Read Order

1. `README.md`
2. `context/index.md`
3. `context/implementation.md`
4. The topic docs linked from `context/index.md` that match the task

## How To Use The Context System

- Start with `context/index.md` for navigation and task routing.
- Treat each topic file under `context/` as the source of truth for that topic.
- Use the ADRs under `context/decisions/` for durable architectural decisions.
- Use `context/implementation.md` for phase status only, not for deep design
  detail.

## Documentation Discipline

- If a change affects product goals, architecture, workflow, repo layout, or
  terminology, update the matching file in `context/` in the same change.
- If a durable technical decision changes, add or update an ADR in
  `context/decisions/`.
- Keep Markdown filenames lowercase.
- Prefer one source of truth per topic. Link across docs instead of repeating
  the same explanation.
- Keep docs concise and scannable for both humans and AI agents.

## Phase Tracking Rules

- `context/implementation.md` is the authoritative phase tracker.
- When a phase finishes, mark it `Completed`, move the next phase to
  `In Progress`, and add a short dated note.
- Do not silently change the phase order or rename phases without updating the
  tracker and supporting docs.

## Repo Conventions

- Use `storage/` as the parent local data directory.
- Keep uploaded media under `storage/uploads/`.
- Keep generated derivatives or previews under `storage/generated/`.
- Keep the local SQLite database under `storage/db/`.
- Do not bypass `.env` for credentials or platform configuration.
- Do not add feature code from later phases when the current task is
  documentation-only.

## Common Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
ruff check .
black --check .
pytest
```
