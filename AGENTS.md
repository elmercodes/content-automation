# AGENTS.md

## Purpose

This repository builds a local-first social media publishing application that runs on a user's machine with a Python backend and server-rendered HTML only. The project is intentionally simple: no cloud assumptions, no JavaScript frontend, no scheduling system, and no deep analytics layer.

## Non-Negotiable Constraints

- Local-only architecture
- Python backend
- FastAPI + Jinja2 templates
- No JavaScript frontend
- SQLite stored locally
- Secrets in `.env`
- Uploaded and generated media stored under `storage/`
- Carousel media modeled as first-class ordered items

## Recommended Read Order

1. `README.md`
2. `context/index.md`
3. `context/implementation.md`

## Repo Conventions

- Keep Markdown filenames lowercase.
- Use `storage/` as the parent local data directory.
- Treat `context/implementation.md` as the source of truth for phase status.
- Update `context/implementation.md` immediately after a phase is completed.
- Do not introduce JavaScript for UI behavior unless the product direction changes explicitly.

## Phase 1 Focus

Phase 1 establishes:

- Python project bootstrap
- dependency and tool configuration
- virtual environment workflow
- minimal FastAPI/Jinja2 localhost app
- local storage conventions
- Alembic scaffold
- AI-agent documentation backbone

## Deferred Until Later Phases

- Database tables and migrations
- Upload handling
- Platform-specific adapters
- Preview generation
- Carousel workflows
- Posting results and history UI

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
