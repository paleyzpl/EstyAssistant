"""Apply subtle text watermark to images for preview/mockup protection."""

import io
import logging

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def apply_watermark(
    image_bytes: bytes,
    text: str = "Carrot Sketches",
    opacity: float = 0.15,
    font_size: int = 36,
) -> bytes:
    """Apply a diagonal text watermark to an image.

    Args:
        image_bytes: Input image bytes (JPEG/PNG).
        text: Watermark text.
        opacity: Watermark opacity (0-1).
        font_size: Base font size (auto-scaled to image).

    Returns:
        Watermarked image as JPEG bytes.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size

    # Scale font to image size
    scale = min(w, h) / 600
    actual_size = max(int(font_size * scale), 16)

    # Create watermark layer
    watermark = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", actual_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    alpha = int(255 * opacity)

    # Tile the watermark diagonally across the image
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    spacing_x = tw + actual_size * 3
    spacing_y = th + actual_size * 4

    for y in range(-h, h * 2, spacing_y):
        for x in range(-w, w * 2, spacing_x):
            draw.text((x, y), text, fill=(128, 128, 128, alpha), font=font)

    # Rotate the watermark layer
    watermark = watermark.rotate(30, expand=False, center=(w // 2, h // 2))

    # Composite
    result = Image.alpha_composite(img, watermark)
    result = result.convert("RGB")

    buf = io.BytesIO()
    result.save(buf, "JPEG", quality=90)
    data = buf.getvalue()
    logger.info("Applied watermark to image (%.0f KB)", len(data) / 1024)
    return data
