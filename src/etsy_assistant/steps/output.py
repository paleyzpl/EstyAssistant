import io
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from etsy_assistant.config import PipelineConfig

logger = logging.getLogger(__name__)


def _to_pil(image: np.ndarray) -> Image.Image:
    """Convert a BGR/grayscale numpy array to a PIL Image."""
    if len(image.shape) == 2:
        return Image.fromarray(image, mode="L")
    rgb = image[:, :, ::-1]  # BGR to RGB
    return Image.fromarray(rgb, mode="RGB")


def encode_output(
    image: np.ndarray,
    dpi: int = 300,
    fmt: str = "PNG",
) -> bytes:
    """Encode a processed image to bytes with DPI metadata.

    Returns the image file content as bytes (no disk I/O).
    """
    pil_image = _to_pil(image)
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt, dpi=(dpi, dpi))
    data = buf.getvalue()
    h, w = image.shape[:2]
    logger.info("Encoded %s image (%dx%d, %.0f KB)", fmt, w, h, len(data) / 1024)
    return data


def save_output(
    image: np.ndarray,
    output_path: Path,
    dpi: int,
    config: PipelineConfig,
) -> Path:
    """Save processed image as PNG with DPI metadata."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Detect format from file extension, falling back to config default
    ext_formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG",
                   ".tif": "TIFF", ".tiff": "TIFF", ".webp": "WEBP"}
    fmt = ext_formats.get(output_path.suffix.lower(), config.output_format)

    data = encode_output(image, dpi, fmt)
    output_path.write_bytes(data)

    size_kb = len(data) / 1024
    h, w = image.shape[:2]
    logger.info("Saved %s (%dx%d, %.0f KB)", output_path, w, h, size_kb)
    return output_path
