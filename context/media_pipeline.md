# Media Pipeline

Media stays on local disk. The backend references media records in SQLite, while
the actual files live under `storage/`.

## Current Baseline

- `storage/uploads/` exists for user-provided files.
- `storage/generated/` exists for future local derivatives.
- Storage directories are created during app startup if missing.
- Phase 5 stores compose uploads under `storage/uploads/posts/<post_id>/`.
- Phase 5 currently accepts image uploads only: JPG, PNG, and WEBP.

## Direction

- Treat each attached file as a `media item` linked to a master post.
- Keep file handling local-first with no remote object storage.
- Preserve explicit order for multi-image carousel posts.
- Separate uploaded originals from generated derivatives or normalized outputs.

## Lifecycle Stages

1. Media enters the app as an uploaded local file.
2. The app saves the original file locally with a unique stored filename.
3. The app records media metadata including original filename, width, height,
   relative file path, and display order.
4. Later phases may create generated or normalized variants under
   `storage/generated/`.
5. Posting workflows use the ordered media item set attached to the master post.

## Phase 5 Upload Rules

- Upload order becomes the saved `display_order`.
- The upload pipeline rejects empty files, unsupported file types, unreadable
  images, and submissions with more than 10 files.
- Failed submissions clean up saved files and keep SQLite free of partial master
  posts or media items.
- Video intake is deferred until later phases add metadata extraction and
  preview support for that media type.

## Validation Boundaries

- Validate media compatibility before posting.
- Keep platform-specific media limits out of templates.
- Treat carousel rules as first-class validation rules, not as a special-case
  hack around single-media posting.

## Related Docs

- [`database.md`](database.md) for record ownership
- [`platform_registry.md`](platform_registry.md) for platform capability
  direction
- [`decisions/006_carousel_first_class_support.md`](decisions/006_carousel_first_class_support.md)
  for the carousel decision
