# Local-First Social Publisher

Local-First Social Publisher is a local-only social media publishing tool built
with Python, FastAPI, Jinja2, SQLite, and the local filesystem. It lets you
create one master post, attach ordered media items, connect provider accounts
through OAuth, preview platform-aware output, submit where direct posting is
supported, and keep a lightweight local history without a JavaScript frontend.

## Current provider support

| Platform | App config in `.env` | Account connection | Direct posting | Notes |
| --- | --- | --- | --- | --- |
| Instagram | `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET` | Yes | No | Professional-account connection is supported. Preview/review stays available after connect, but direct posting still needs public media URLs that the current local-only workflow does not provide. |
| Facebook | `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET` | Yes | Yes | Login plus managed Page selection is supported. Single-image posts upload directly to the connected Facebook Page with the stored local Page token. |
| X | `X_CLIENT_ID` | Yes | Yes | Uses OAuth 2.0 with PKCE for account connection, stores tokens locally in SQLite, and posts through the stored connected-account tokens. |

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
./scripts/generate_localhost_https_cert.sh
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --ssl-keyfile storage/certs/localhost-key.pem --ssl-certfile storage/certs/localhost-cert.pem
```

Open `https://localhost:8000/`.

App startup creates missing local directories and auto-applies pending Alembic
migrations for the configured SQLite database.

## `.env` setup notes

- Copy `.env.example` to `.env` before the first run.
- `.env` is now only for app-level runtime and provider app configuration.
- Do not put user access tokens, refresh tokens, token secrets, or Page IDs in
  `.env`.
- Restart the app after editing `.env` because settings are cached in-process.
- Only local SQLite database URLs are supported.
- For Facebook and Instagram OAuth, `APP_BASE_URL` should be an HTTPS URL that
  matches the browser origin and the provider dashboard callback entry.

## Local HTTPS for Meta OAuth

Facebook and Instagram OAuth will reject the default insecure local callback
origin. This repo includes a small helper for a local self-signed certificate:

```bash
./scripts/generate_localhost_https_cert.sh
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --ssl-keyfile storage/certs/localhost-key.pem --ssl-certfile storage/certs/localhost-cert.pem
```

Use `https://localhost:8000` as the browser URL and set this exact callback URL
in the Meta developer dashboard:

- `https://localhost:8000/oauth/callback/facebook`
- `https://localhost:8000/oauth/callback/instagram`

The certificate is self-signed, so the browser may ask you to accept a local
warning once.

## First local run

1. Open `Accounts` and connect any provider accounts you want to use.
2. Open `Compose` and create a master post with 1 or more JPG, PNG, or WEBP
   images.
3. Continue to `Platforms` and choose from the connected platforms that are
   eligible for the current post.
4. Review one selected platform at a time with generated local previews.
5. Submit from `Final review` where direct posting is supported.
6. Inspect the immediate `Results` page, then browse the longer-lived `History`
   ledger.

For Facebook direct posting, reconnect the Page once if it was connected before
`pages_manage_posts` was added to the requested OAuth scopes.

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

- `storage/db/` holds the SQLite database, including connected-account tokens.
- `storage/uploads/` holds original uploaded media.
- `storage/generated/` holds regenerable preview artifacts.
- App startup creates missing directories and upgrades the local schema to the
  latest Alembic revision.

## Database and migrations

App startup automatically upgrades the configured SQLite database to the latest
schema. You can still run migrations manually for recovery, CI, or explicit
local setup:

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

- A provider is missing from `Accounts`:
  - Check the provider app settings in `.env`, then restart the app.
- A provider is visible in `Accounts` but not on `Platforms`:
  - Connect or reconnect the provider account, then return to the workflow.
- X is connected but not ready to submit:
  - Reconnect X and grant the requested OAuth scopes.
- Facebook is connected but not ready to submit:
  - Reconnect Facebook and grant `pages_manage_posts`.
- Startup fails because the local schema could not be upgraded:
  - Run `.venv/bin/alembic upgrade head`.
- Uploaded media or previews are missing:
  - Check the local `storage/uploads/` and `storage/generated/` directories.

## Project status

- The implementation tracker lives in
  [`context/implementation.md`](context/implementation.md).
