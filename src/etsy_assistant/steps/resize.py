import logging

import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig

logger = logging.getLogger(__name__)

PRINT_SIZES: dict[str, tuple[float, float]] = {
    "5x7": (5.0, 7.0),
    "8x10": (8.0, 10.0),
    "11x14": (11.0, 14.0),
    "16x20": (16.0, 20.0),
    "A4": (8.27, 11.69),
}


def resize_for_print(
    image: np.ndarray,
    size_name: str | None,
    dpi: int,
    config: PipelineConfig,
) -> np.ndarray:
    """Resize image to a standard print size at given DPI.

    Fits the image within the target dimensions while preserving aspect ratio,
    centered on a white canvas.
    """
    if size_name is None:
        return image

    size_key = size_name.upper() if size_name.upper() == "A4" else size_name.lower()
    if size_key not in PRINT_SIZES:
        valid = ", ".join(PRINT_SIZES)
        raise ValueError(f"Unknown size '{size_name}'. Valid sizes: {valid}")

    w_inches, h_inches = PRINT_SIZES[size_key]
    target_w = int(w_inches * dpi)
    target_h = int(h_inches * dpi)

    src_h, src_w = image.shape[:2]

    # Match orientation: if source is landscape, swap target dimensions
    src_landscape = src_w > src_h
    target_landscape = target_w > target_h
    if src_landscape != target_landscape:
        target_w, target_h = target_h, target_w

    # Scale to fit within target, preserving aspect ratio
    scale = min(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    interpolation = cv2.INTER_LANCZOS4 if scale < 1 else cv2.INTER_CUBIC
    resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    # Center on white canvas
    if len(image.shape) == 3:
        canvas = np.full((target_h, target_w, image.shape[2]), 255, dtype=np.uint8)
    else:
        canvas = np.full((target_h, target_w), 255, dtype=np.uint8)

    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

    logger.info("Resized to %s (%dx%d px at %d DPI)", size_name, target_w, target_h, dpi)
    return canvas
