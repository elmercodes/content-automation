# ADR 007: Preview Artifacts Are Regenerable Local Derivatives

- Status: Accepted
- Date: 2026-04-16

## Decision

Treat generated preview files as local regenerable derivatives stored under
`storage/generated/`, not as primary records in SQLite.

## Rationale

- Phase 7 needs real preview output without expanding the schema.
- Preview artifacts are derived from a saved master post, ordered media items,
  and backend platform registry metadata.
- Persisting preview files locally keeps the review step fast and simple while
  preserving uploaded originals unchanged.
- A deterministic no-crop normalization rule provides useful previews now
  without committing the app to pixel-perfect provider UI cloning.

## Alternatives Not Chosen

- Store preview metadata or preview file paths in new database tables
- Generate preview images only in memory on every request
- Crop images by default to fill each platform canvas

## Consequences

- Preview files can be reused when they are newer than their source upload and
  regenerated when missing or stale.
- Phase 7 can stay single-image-first while keeping later carousel preview work
  compatible with the same local artifact approach.
- Cleanup policy for stale generated previews remains deferred until later
  history or edit workflows require it.
