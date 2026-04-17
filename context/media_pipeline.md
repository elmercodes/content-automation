# Media Pipeline

Media stays on local disk. The backend references media records in SQLite, while
the actual files live under `storage/`.

## Current Baseline

- `storage/uploads/` exists for user-provided files.
- `storage/generated/` exists for future local derivatives.
- Storage directories are created during app startup if missing.
- Phase 5 stores compose uploads under `storage/uploads/posts/<post_id>/`.
- Phase 5 currently accepts image uploads only: JPG, PNG, and WEBP.
- Phase 7 stores generated preview files under
  `storage/generated/previews/v1/posts/<post_id>/<platform_slug>/media-<display_order>.png`.
- Phase 10 exposes uploaded originals through a narrow backend route so history
  pages can render local thumbnails without mounting all of `storage/`.

## Direction

- Treat each attached file as a `media item` linked to a master post.
- Keep file handling local-first with no remote object storage.
- Preserve explicit order for multi-image carousel posts.
- Separate uploaded originals from generated derivatives or normalized outputs.
- Preserve the uploaded original by default. Preview generation should create a
  derived file instead of mutating the original asset.

## Lifecycle Stages

1. Media enters the app as an uploaded local file.
2. The app saves the original file locally with a unique stored filename.
3. The app records media metadata including original filename, width, height,
   relative file path, and display order.
4. Phase 7 can create generated preview variants under `storage/generated/`
   without changing the saved upload.
5. Preview normalization resizes proportionally, centers the image on a new
   platform-owned canvas, and avoids default cropping.
6. Phase 9 posting workflows use the ordered original media item set attached
   to the master post rather than reusing generated preview artifacts.
7. Phase 10 history views reuse the saved original uploads for thumbnail-style
   rendering and degrade gracefully when a local file is missing.

## Phase 5 Upload Rules

- Upload order becomes the saved `display_order`.
- The upload pipeline rejects empty files, unsupported file types, unreadable
  images, and submissions with more than 10 files.
- Failed submissions clean up saved files and keep SQLite free of partial master
  posts or media items.
- Video intake is deferred until later phases add metadata extraction and
  preview support for that media type.

## Phase 8 Preview Rules

- Preview generation is deterministic and regenerable.
- Generated preview files are local artifacts, not durable primary records.
- Phase 8 generates one preview artifact per ordered media item for the current
  platform review step.
- The review workflow renders all ordered image items for eligible carousel
  platforms without introducing a JavaScript gallery.
- The default background strategy is a neutral solid canvas fill rather than
  image-aware gradients or automatic cropping.

## Validation Boundaries

- Validate media compatibility before posting.
- Validate that the selected local source files still exist and are readable
  before provider submission begins.
- Keep platform-specific media limits out of templates.
- Treat carousel rules as first-class validation rules, not as a special-case
  hack around single-media posting.

## Related Docs

- [`database.md`](database.md) for record ownership
- [`platform_registry.md`](platform_registry.md) for platform capability
  direction
- [`decisions/006_carousel_first_class_support.md`](decisions/006_carousel_first_class_support.md)
  for the carousel decision
