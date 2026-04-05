import logging
from pathlib import Path

import numpy as np
from PIL import Image

from etsy_assistant.config import PipelineConfig

logger = logging.getLogger(__name__)


def save_output(
    image: np.ndarray,
    output_path: Path,
    dpi: int,
    config: PipelineConfig,
) -> Path:
    """Save processed image as PNG with DPI metadata."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(image.shape) == 2:
        pil_image = Image.fromarray(image, mode="L")
    else:
        rgb = image[:, :, ::-1]  # BGR to RGB
        pil_image = Image.fromarray(rgb, mode="RGB")

    # Detect format from file extension, falling back to config default
    ext_formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG",
                   ".tif": "TIFF", ".tiff": "TIFF", ".webp": "WEBP"}
    fmt = ext_formats.get(output_path.suffix.lower(), config.output_format)
    pil_image.save(str(output_path), format=fmt, dpi=(dpi, dpi))

    size_kb = output_path.stat().st_size / 1024
    h, w = image.shape[:2]
    logger.info("Saved %s (%dx%d, %.0f KB)", output_path, w, h, size_kb)
    return output_path
