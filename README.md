# Local-First Social Publisher

Local-First Social Publisher is a local-only social media publishing tool built
with Python, FastAPI, Jinja2, SQLite, and the local filesystem. It lets you
create one master post, attach ordered media items, preview platform-aware
output, submit where direct posting is supported, and keep a lightweight local
history without a JavaScript frontend or any cloud dependency.

## Current provider support

| Platform | Visible when configured | Review/preview | Direct posting | Notes |
| --- | --- | --- | --- | --- |
| Instagram | `INSTAGRAM_ACCESS_TOKEN` | Yes | No | Image-only single posts and carousels can move through review. Direct posting is intentionally deferred in the current local-only model. |
| Facebook | `FACEBOOK_PAGE_ID` | Yes | Yes for preview only | No | Image-only single posts can move through review. Carousel posting is not supported in the current workflow. |
| X | `X_API_KEY` | Yes | Yes | Image-only single posts and carousels up to 4 images. Real posting requires `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_TOKEN_SECRET`. |

## Requirements

- Python 3.12
- `python3 -m venv`
- A local browser

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
cp .env.example .env
.venv/bin/alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

## `.env` setup notes

- Copy `.env.example` to `.env` before the first run.
- Leave provider values empty if you want to explore the app without configured
  platforms.
- Platform visibility and direct posting are different:
  - `INSTAGRAM_ACCESS_TOKEN` makes Instagram visible in the workflow, but direct
    posting is still deferred.
  - `FACEBOOK_PAGE_ID` makes Facebook visible in the workflow, but direct
    posting is still deferred.
  - `X_API_KEY` makes X visible in the workflow.
  - X direct posting additionally requires `X_API_SECRET`,
    `X_ACCESS_TOKEN`, and `X_ACCESS_TOKEN_SECRET`.
- Restart the app after editing `.env` because settings are cached in-process.
- Only local SQLite database URLs are supported.

## First local run

1. Open `Compose` and create a master post with 1 or more JPG, PNG, or WEBP
   images.
2. Continue to `Platforms` and choose from the platforms that are configured on
   your machine.
3. Review one selected platform at a time with generated local previews.
4. Submit from `Final review` where direct posting is supported.
5. Inspect the immediate `Results` page, then browse the longer-lived `History`
   ledger.

## Local data layout

The app keeps all state on disk under `storage/`:

```text
storage/
├── db/
│   └── app.db
├── generated/
│   └── previews/
└── uploads/
    └── posts/
```

- `storage/db/` holds the SQLite database.
- `storage/uploads/` holds original uploaded media.
- `storage/generated/` holds regenerable preview artifacts.
- App startup creates missing directories.
- Alembic migrations create and upgrade the database schema.

## Database and migrations

Run the current schema on a clean checkout with:

```bash
.venv/bin/alembic upgrade head
```

The default database file is `storage/db/app.db`.

## Verify

```bash
ruff check .
black --check .
pytest
```

## Troubleshooting

- No platforms are visible:
  - Check `.env`, then restart the app.
- X is visible but not ready to submit:
  - Add `X_API_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_TOKEN_SECRET` in
    addition to `X_API_KEY`.
- A fresh checkout shows missing tables:
  - Run `.venv/bin/alembic upgrade head`.
- Uploaded media or previews are missing:
  - Check the local `storage/uploads/` and `storage/generated/` directories.

## Project status

- All planned roadmap phases are complete.
- The implementation tracker lives in
  [`context/implementation.md`](context/implementation.md).
