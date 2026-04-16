from __future__ import annotations

import time
from pathlib import Path

from PIL import Image

from app.config import Settings
from app.image_normalization import generate_platform_preview_file
from app.platform_selection_service import WorkflowMediaItemSummary
from app.platforms import PlatformPreviewSpec


def build_test_settings(tmp_path: Path) -> Settings:
    storage_root = tmp_path / "storage"
    uploads_dir = storage_root / "uploads"
    generated_dir = storage_root / "generated"
    database_path = storage_root / "db" / "app.db"
    for path in (uploads_dir, generated_dir, database_path.parent):
        path.mkdir(parents=True, exist_ok=True)
    return Settings(
        _env_file=None,
        storage_root=storage_root,
        uploads_dir=uploads_dir,
        generated_dir=generated_dir,
        database_url=f"sqlite:///{database_path}",
    )


def create_source_image(
    settings: Settings,
    *,
    post_id: int,
    display_order: int,
    size: tuple[int, int],
    color: tuple[int, int, int],
) -> WorkflowMediaItemSummary:
    relative_path = (
        Path("uploads") / "posts" / str(post_id) / f"{display_order:03d}-source.png"
    )
    absolute_path = settings.storage_root_path / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(absolute_path, format="PNG")
    return WorkflowMediaItemSummary(
        display_order=display_order,
        original_filename=f"source-{display_order}.png",
        media_type="image",
        width=size[0],
        height=size[1],
        file_path=relative_path.as_posix(),
    )


def test_generate_platform_preview_file_contains_image_on_fixed_canvas(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)
    media_item = create_source_image(
        settings,
        post_id=12,
        display_order=0,
        size=(40, 20),
        color=(20, 40, 60),
    )

    artifact = generate_platform_preview_file(
        media_item,
        post_id=12,
        platform_slug="instagram",
        preview_spec=PlatformPreviewSpec(
            canvas_width=100,
            canvas_height=100,
            frame_label="Test canvas",
        ),
        settings=settings,
    )

    with Image.open(artifact.absolute_path) as preview_image:
        preview_image.load()
        assert preview_image.size == (100, 100)
        assert preview_image.getpixel((50, 50)) == (20, 40, 60)
        assert preview_image.getpixel((50, 10)) == (246, 242, 234)


def test_generate_platform_preview_file_reuses_output_until_source_changes(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)
    media_item = create_source_image(
        settings,
        post_id=8,
        display_order=0,
        size=(32, 32),
        color=(80, 50, 30),
    )
    preview_spec = PlatformPreviewSpec(
        canvas_width=120,
        canvas_height=120,
        frame_label="Reuse test",
    )

    first_artifact = generate_platform_preview_file(
        media_item,
        post_id=8,
        platform_slug="x",
        preview_spec=preview_spec,
        settings=settings,
    )
    first_mtime = first_artifact.absolute_path.stat().st_mtime_ns

    second_artifact = generate_platform_preview_file(
        media_item,
        post_id=8,
        platform_slug="x",
        preview_spec=preview_spec,
        settings=settings,
    )
    second_mtime = second_artifact.absolute_path.stat().st_mtime_ns

    assert second_artifact.absolute_path == first_artifact.absolute_path
    assert second_mtime == first_mtime

    time.sleep(0.02)
    source_path = settings.storage_root_path / media_item.file_path
    source_path.touch()

    third_artifact = generate_platform_preview_file(
        media_item,
        post_id=8,
        platform_slug="x",
        preview_spec=preview_spec,
        settings=settings,
    )

    assert third_artifact.absolute_path.stat().st_mtime_ns > second_mtime
