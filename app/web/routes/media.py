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
    generated_root = settings.generated_path.resolve()
    requested_path = (generated_root / Path(preview_path)).resolve()

    if not requested_path.is_relative_to(generated_root):
        raise HTTPException(status_code=404, detail="Generated preview not found.")

    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Generated preview not found.")

    return FileResponse(requested_path)
