import logging

import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig

logger = logging.getLogger(__name__)


def autocrop(image: np.ndarray, config: PipelineConfig) -> np.ndarray:
    """Detect sketch edges and crop to content, removing surrounding desk/table."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    blurred = cv2.GaussianBlur(gray, (config.crop_blur_kernel, config.crop_blur_kernel), 0)
    _, binary = cv2.threshold(blurred, config.crop_threshold, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        logger.warning("No contours found, returning original image")
        return image

    largest = max(contours, key=cv2.contourArea)
    h, w = image.shape[:2]
    if cv2.contourArea(largest) < 0.01 * h * w:
        logger.warning("Largest contour too small, returning original image")
        return image

    x, y, cw, ch = cv2.boundingRect(largest)
    margin = config.crop_margin_px
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(w, x + cw + margin)
    y2 = min(h, y + ch + margin)

    cropped = image[y1:y2, x1:x2]
    logger.info("Cropped from %dx%d to %dx%d", w, h, x2 - x1, y2 - y1)
    return cropped
