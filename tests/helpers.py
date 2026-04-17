from __future__ import annotations

from io import BytesIO

from httpx import AsyncClient
from PIL import Image


def make_image_bytes(*, image_format: str = "PNG", size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", size, color=(70, 50, 40))
    image.save(buffer, format=image_format)
    return buffer.getvalue()


async def create_master_post(
    client: AsyncClient,
    *,
    media_sizes: list[tuple[int, int]],
    caption: str = "Launch locally",
    hashtags: str = "#local",
) -> int:
    files = [
        (
            "media_files",
            (
                f"image-{index}.png",
                make_image_bytes(size=media_size),
                "image/png",
            ),
        )
        for index, media_size in enumerate(media_sizes)
    ]
    response = await client.post(
        "/compose",
        data={"caption": caption, "hashtags": hashtags},
        files=files,
        follow_redirects=False,
    )

    assert response.status_code == 303
    return int(response.headers["location"].split("post_id=")[1])
