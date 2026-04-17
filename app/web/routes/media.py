from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter()


@router.get(
    "/media/generated/{preview_path:path}",
    name="generated_media",
    response_class=FileResponse,
)
async def generated_media(preview_path: str) -> FileResponse:
    settings = get_settings()
    requested_path = _resolve_local_media_path(
        root_path=settings.generated_path.resolve(),
        relative_path=preview_path,
        not_found_detail="Generated preview not found.",
    )
    return FileResponse(requested_path)


@router.get(
    "/media/uploads/{upload_path:path}",
    name="uploaded_media",
    response_class=FileResponse,
)
async def uploaded_media(upload_path: str) -> FileResponse:
    settings = get_settings()
    requested_path = _resolve_local_media_path(
        root_path=settings.uploads_path.resolve(),
        relative_path=upload_path,
        not_found_detail="Uploaded media not found.",
    )
    return FileResponse(requested_path)


def _resolve_local_media_path(
    *,
    root_path: Path,
    relative_path: str,
    not_found_detail: str,
) -> Path:
    requested_path = (root_path / Path(relative_path)).resolve()

    if not requested_path.is_relative_to(root_path):
        raise HTTPException(status_code=404, detail=not_found_detail)

    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail=not_found_detail)

    return requested_path
