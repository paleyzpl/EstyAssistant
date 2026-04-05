import logging

import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig

logger = logging.getLogger(__name__)


def enhance_contrast(image: np.ndarray, config: PipelineConfig) -> np.ndarray:
    """Enhance ink line contrast using CLAHE and levels adjustment."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    # CLAHE for local contrast enhancement (mild to avoid amplifying paper texture)
    clahe = cv2.createCLAHE(
        clipLimit=config.contrast_clip_limit,
        tileGridSize=(config.contrast_tile_size, config.contrast_tile_size),
    )
    enhanced = clahe.apply(gray)

    # Levels adjustment: clamp darks to black, lights to white
    result = enhanced.astype(np.float32)
    floor = config.ink_darkness_floor
    ceiling = config.white_ceiling
    result = np.clip((result - floor) / (ceiling - floor) * 255, 0, 255).astype(np.uint8)

    # Gamma correction to darken ink lines while preserving smooth gradients
    gamma = 0.7
    lut = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
    result = lut[result]

    # Push near-white pixels to pure white (removes faint paper texture remnants)
    result[result > 230] = 255

    # Very gentle sharpening to preserve smooth pen strokes
    blurred = cv2.GaussianBlur(result, (0, 0), sigmaX=1.5)
    result = cv2.addWeighted(result, 1.15, blurred, -0.15, 0)

    logger.info("Contrast enhanced (CLAHE + levels + sharpen)")
    return result
