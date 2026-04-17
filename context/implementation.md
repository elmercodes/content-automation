# Implementation Tracker

## Status

- OAuth Connected Accounts Migration: Completed

## 2026-04-17

- Replaced env-driven platform user auth with OAuth-based connected accounts.
- Added `connected_accounts` and `oauth_connection_attempts` persistence.
- Added server-rendered account connection routes and pages.
- Migrated X posting to use stored OAuth-derived tokens.
- Updated docs and tests to the connected-account architecture.
