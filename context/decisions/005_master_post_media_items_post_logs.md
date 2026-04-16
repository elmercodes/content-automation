# ADR 005: Master Post, Media Items, and Post Platform Logs

- Status: Accepted
- Date: 2026-04-15

## Decision

Model the core publishing workflow around master posts, ordered media items, and
post platform logs, mapping to the future tables `posts`, `media_items`, and
`post_platform_logs`.

## Rationale

- The app needs one shared post concept that can be published to multiple
  platforms.
- Media attachments need their own durable records and ordering.
- Platform outcomes need to be tracked separately from the main post record.

## Alternatives Not Chosen

- Single flat record that mixes post, media, and platform outcome data
- Platform-specific post records as the primary model

## Consequences

- Future database and workflow design should preserve this separation of
  concerns.
- History views can stay lightweight while still showing per-platform outcomes.
- Media ordering remains durable instead of being inferred from filenames or
  upload timing.
