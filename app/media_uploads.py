"""Helpers for validating, saving, and cleaning up uploaded media items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import Settings, get_settings

ALLOWED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_MEDIA_FILES = 10
UPLOAD_CHUNK_SIZE = 1024 * 1024
ORIGINAL_FILENAME_LIMIT = 255


class MediaUploadValidationError(ValueError):
    """Raised when an uploaded file fails Phase 5 validation."""


@dataclass(frozen=True, slots=True)
class SavedMediaMetadata:
    """Metadata captured for one saved uploaded file."""

    absolute_path: Path
    relative_path: str
    original_filename: str
    media_type: str
    width: int
    height: int
    display_order: int


def sanitize_original_filename(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).name.strip()[:ORIGINAL_FILENAME_LIMIT]


def validate_media_selection(media_files: list[UploadFile] | None) -> list[str]:
    files = list(media_files or [])
    errors: list[str] = []

    if not files:
        return ["Select at least one image to create a master post."]

    if len(files) > MAX_MEDIA_FILES:
        errors.append(f"Select up to {MAX_MEDIA_FILES} images per master post.")

    blank_filenames = [
        index + 1
        for index, upload in enumerate(files)
        if not sanitize_original_filename(upload.filename)
    ]
    if blank_filenames:
        errors.append("Each selected file must include a filename.")

    unsupported_files = [
        sanitize_original_filename(upload.filename) or f"upload {index + 1}"
        for index, upload in enumerate(files)
        if sanitize_original_filename(upload.filename)
        and Path(sanitize_original_filename(upload.filename)).suffix.lower()
        not in ALLOWED_IMAGE_EXTENSIONS
    ]
    if unsupported_files:
        joined_names = ", ".join(unsupported_files)
        errors.append(
            "Unsupported file type for "
            f"{joined_names}. Use JPG, PNG, or WEBP images only."
        )

    return errors


def save_uploaded_image(
    upload: UploadFile,
    *,
    post_id: int,
    display_order: int,
    settings: Settings | None = None,
) -> SavedMediaMetadata:
    resolved_settings = settings or get_settings()
    original_filename = sanitize_original_filename(upload.filename)
    if not original_filename:
        raise MediaUploadValidationError("Each selected file must include a filename.")

    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise MediaUploadValidationError(
            f"{original_filename} is not a supported image file."
        )

    destination_dir = resolved_settings.uploads_path / "posts" / str(post_id)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / f"{display_order:03d}-{uuid4().hex}{suffix}"

    try:
        upload.file.seek(0)
    except (AttributeError, OSError):
        pass

    bytes_written = 0
    try:
        with destination_path.open("wb") as buffer:
            while True:
                chunk = upload.file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                buffer.write(chunk)
                bytes_written += len(chunk)

        if bytes_written == 0:
            raise MediaUploadValidationError(f"{original_filename} is empty.")

        try:
            with Image.open(destination_path) as image:
                image.load()
                width, height = image.size
        except (UnidentifiedImageError, OSError) as exc:
            raise MediaUploadValidationError(
                f"{original_filename} is not a readable image."
            ) from exc

        relative_path = destination_path.relative_to(
            resolved_settings.storage_root_path
        ).as_posix()
        return SavedMediaMetadata(
            absolute_path=destination_path,
            relative_path=relative_path,
            original_filename=original_filename,
            media_type="image",
            width=width,
            height=height,
            display_order=display_order,
        )
    except Exception:
        destination_path.unlink(missing_ok=True)
        raise


def cleanup_saved_files(
    saved_paths: list[Path],
    *,
    settings: Settings | None = None,
) -> None:
    resolved_settings = settings or get_settings()
    parent_paths = {path.parent for path in saved_paths}

    for path in saved_paths:
        path.unlink(missing_ok=True)

    for parent in sorted(parent_paths, key=lambda path: len(path.parts), reverse=True):
        _remove_empty_directories(parent, stop_path=resolved_settings.uploads_path)


def cleanup_post_upload_directory(
    post_id: int,
    *,
    settings: Settings | None = None,
) -> None:
    resolved_settings = settings or get_settings()
    _remove_empty_directories(
        resolved_settings.uploads_path / "posts" / str(post_id),
        stop_path=resolved_settings.uploads_path,
    )


def _remove_empty_directories(path: Path, *, stop_path: Path) -> None:
    current_path = path
    while current_path != stop_path and current_path.exists():
        try:
            current_path.rmdir()
        except OSError:
            break
        current_path = current_path.parent
