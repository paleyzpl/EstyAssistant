import logging
from pathlib import Path

import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig
from etsy_assistant.steps.autocrop import autocrop
from etsy_assistant.steps.background import cleanup_background
from etsy_assistant.steps.contrast import enhance_contrast
from etsy_assistant.steps.output import save_output
from etsy_assistant.steps.perspective import correct_perspective
from etsy_assistant.steps.resize import resize_for_print

logger = logging.getLogger(__name__)

STEP_FUNCTIONS = {
    "autocrop": autocrop,
    "perspective": correct_perspective,
    "background": cleanup_background,
    "contrast": enhance_contrast,
}

STEP_ORDER = ["autocrop", "perspective", "background", "contrast"]


def _save_debug(image: np.ndarray, debug_dir: Path, step_index: int, step_name: str) -> None:
    """Save intermediate image for debugging."""
    debug_dir.mkdir(parents=True, exist_ok=True)
    path = debug_dir / f"{step_index:02d}_{step_name}.png"
    if len(image.shape) == 2:
        cv2.imwrite(str(path), image)
    else:
        cv2.imwrite(str(path), image)
    logger.debug("Debug image saved: %s", path)


def process_image(
    input_path: Path,
    output_path: Path,
    sizes: list[str] | None = None,
    config: PipelineConfig | None = None,
    skip_steps: set[str] | None = None,
    debug: bool = False,
) -> list[Path]:
    """Run the full image cleanup pipeline.

    Returns list of output file paths (one per size, or one if no sizes specified).
    """
    config = config or PipelineConfig()
    skip_steps = skip_steps or set()
    input_path = Path(input_path)

    image = cv2.imread(str(input_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {input_path}")

    logger.info("Processing %s (%dx%d)", input_path.name, image.shape[1], image.shape[0])

    debug_dir = input_path.parent / "debug" if debug else None

    if debug:
        _save_debug(image, debug_dir, 0, "original")

    # Run pipeline steps
    for i, step_name in enumerate(STEP_ORDER, start=1):
        if step_name in skip_steps:
            logger.info("Skipping step: %s", step_name)
            continue

        step_fn = STEP_FUNCTIONS[step_name]
        try:
            image = step_fn(image, config)
        except Exception:
            logger.exception("Step '%s' failed, continuing with previous result", step_name)

        if debug:
            _save_debug(image, debug_dir, i, step_name)

    # Resize and save outputs
    output_path = Path(output_path)
    output_paths = []

    if not sizes:
        result = resize_for_print(image, None, config.output_dpi, config)
        path = save_output(result, output_path, config.output_dpi, config)
        output_paths.append(path)
    else:
        # Multiple sizes: output to directory
        if output_path.suffix:
            out_dir = output_path.parent
            stem = output_path.stem
        else:
            out_dir = output_path
            stem = input_path.stem + "_clean"

        for size_name in sizes:
            resized = resize_for_print(image, size_name, config.output_dpi, config)
            size_path = out_dir / f"{stem}_{size_name}.png"
            path = save_output(resized, size_path, config.output_dpi, config)
            output_paths.append(path)

    return output_paths
