"""Compose flow orchestration for master posts and uploaded media items."""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.db import MediaItem, Post
from app.media_uploads import (
    MAX_MEDIA_FILES,
    MediaUploadValidationError,
    cleanup_post_upload_directory,
    cleanup_saved_files,
    save_uploaded_image,
    validate_media_selection,
)


@dataclass(frozen=True, slots=True)
class ComposeFormData:
    """Normalized server-rendered compose form values."""

    caption: str = ""
    hashtags: str = ""


@dataclass(frozen=True, slots=True)
class MasterPostSummary:
    """Minimal state carried from compose into the platforms page."""

    id: int
    caption: str
    hashtags: str
    media_count: int


@dataclass(slots=True)
class ComposeSubmissionResult:
    """Result object returned to the compose route."""

    form: ComposeFormData
    field_errors: dict[str, list[str]] = field(default_factory=dict)
    non_field_errors: list[str] = field(default_factory=list)
    post_id: int | None = None

    @property
    def succeeded(self) -> bool:
        return (
            self.post_id is not None
            and not self.field_errors
            and not self.non_field_errors
        )


def empty_compose_form() -> ComposeFormData:
    return ComposeFormData()


def build_compose_page_context(
    *,
    form: ComposeFormData | None = None,
    field_errors: dict[str, list[str]] | None = None,
    non_field_errors: list[str] | None = None,
) -> dict[str, object]:
    return {
        "compose_form": form or empty_compose_form(),
        "field_errors": field_errors or {},
        "non_field_errors": non_field_errors or [],
        "max_media_files": MAX_MEDIA_FILES,
    }


def create_master_post(
    session: Session,
    *,
    caption: str | None,
    hashtags: str | None,
    media_files: list[UploadFile] | None,
    settings: Settings | None = None,
) -> ComposeSubmissionResult:
    resolved_settings = settings or get_settings()
    form = ComposeFormData(
        caption=_normalize_text(caption),
        hashtags=_normalize_text(hashtags),
    )
    field_errors: dict[str, list[str]] = {}
    media_errors = validate_media_selection(media_files)
    if media_errors:
        field_errors["media_files"] = media_errors
        return ComposeSubmissionResult(form=form, field_errors=field_errors)

    post_id: int | None = None
    saved_paths = []
    try:
        post = Post(caption=form.caption, hashtags=form.hashtags)
        session.add(post)
        session.flush()
        post_id = post.id

        for display_order, upload in enumerate(media_files or []):
            saved_media = save_uploaded_image(
                upload,
                post_id=post.id,
                display_order=display_order,
                settings=resolved_settings,
            )
            saved_paths.append(saved_media.absolute_path)
            session.add(
                MediaItem(
                    post_id=post.id,
                    file_path=saved_media.relative_path,
                    media_type=saved_media.media_type,
                    original_filename=saved_media.original_filename,
                    width=saved_media.width,
                    height=saved_media.height,
                    display_order=saved_media.display_order,
                )
            )

        session.commit()
        return ComposeSubmissionResult(form=form, post_id=post.id)
    except MediaUploadValidationError as exc:
        session.rollback()
        cleanup_saved_files(saved_paths, settings=resolved_settings)
        if post_id is not None:
            cleanup_post_upload_directory(post_id, settings=resolved_settings)
        field_errors["media_files"] = [str(exc)]
        return ComposeSubmissionResult(form=form, field_errors=field_errors)
    except Exception:
        session.rollback()
        cleanup_saved_files(saved_paths, settings=resolved_settings)
        if post_id is not None:
            cleanup_post_upload_directory(post_id, settings=resolved_settings)
        return ComposeSubmissionResult(
            form=form,
            non_field_errors=[
                "The master post could not be saved. No local files were kept."
            ],
        )


def load_master_post_summary(
    session: Session,
    *,
    post_id: int,
) -> MasterPostSummary | None:
    post = session.scalar(
        select(Post).options(selectinload(Post.media_items)).where(Post.id == post_id)
    )
    if post is None:
        return None

    return MasterPostSummary(
        id=post.id,
        caption=post.caption,
        hashtags=post.hashtags,
        media_count=len(post.media_items),
    )


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()
