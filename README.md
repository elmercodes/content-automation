# Local-First Social Publisher

This repository contains a local-first social media publishing application built
with Python, FastAPI, and server-rendered HTML templates. Phase 1 established
the development foundation: local bootstrap, tooling, documentation backbone,
and a minimal localhost smoke app.

## Requirements

- Python 3.12
- `python3 -m venv`

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
cp .env.example .env
.venv/bin/alembic upgrade head
```

## Run Locally

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

## Verify

```bash
ruff check .
black --check .
pytest
```

## Database

Phase 4 adds the local SQLite schema and migration layer. The default database
file lives at `storage/db/app.db` and should be created through Alembic:

```bash
.venv/bin/alembic upgrade head
```

## Current Status

- Phase 1 foundation is complete.
- Phase 2 AI-agent docs system is complete.
- Phase 3 core app skeleton and config is complete.
- Phase 4 database and migrations is complete.
- Phase 5 compose form and upload pipeline is complete.
- Phase 6 platform selection flow is now the current phase.
- See `context/implementation.md` for the roadmap and current phase tracking.
