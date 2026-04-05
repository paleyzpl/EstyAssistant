import logging

import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig

logger = logging.getLogger(__name__)


def cleanup_background(image: np.ndarray, config: PipelineConfig) -> np.ndarray:
    """Turn paper background to pure white while preserving ink lines.

    Uses adaptive thresholding to handle uneven phone camera lighting.
    Returns a grayscale image (pen & ink sketches are monochrome).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    # Blur to reduce paper texture/grain before thresholding
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold: ink pixels become 0 (black), paper becomes 255 (white)
    mask = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        config.bg_adaptive_block_size,
        config.bg_adaptive_c,
    )

    # Morphological open to remove small noise specks (paper texture dots)
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)

    # Then close to fill tiny gaps in thin ink lines
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

    # Where mask says paper (255), force pure white; keep original ink tones
    result = gray.copy()
    result[mask == 255] = 255

    logger.info("Background cleaned to white")
    return result
