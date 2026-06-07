from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from PIL import Image


def encode_frame_jpeg_data_url(frame: Any, quality: int = 75) -> str | None:
    if frame is None:
        return None

    image = Image.fromarray(frame)
    if image.mode != "RGB":
        image = image.convert("RGB")

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
