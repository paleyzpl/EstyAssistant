import io
import json
import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _load_templates() -> dict:
    """Load template metadata."""
    meta_path = TEMPLATE_DIR / "templates.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Template metadata not found at {meta_path}.")
    return json.loads(meta_path.read_text())


def list_templates() -> list[str]:
    """Return available template names."""
    return list(_load_templates().keys())


def _detect_frame_interior(image_path: Path, inset_frac: float = 0.03) -> tuple[int, int, int, int]:
    """Detect the white/blank interior region of a picture frame.

    Uses thresholding + contour detection to find the largest bright
    rectangular region, then insets slightly to avoid frame edges.

    Returns (x, y, x2, y2) bounding box of the interior.
    """
    img = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Threshold to find bright (white/near-white) regions
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # Morphological close to fill small gaps in the white area
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Find contours of white regions
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError(f"Could not detect frame interior in {image_path.name}")

    # Find the largest contour by area that is roughly rectangular
    best = None
    best_area = 0
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        # Must be at least 10% of image in each dimension
        if cw > w * 0.1 and ch > h * 0.1 and area > best_area:
            best = (x, y, cw, ch)
            best_area = area

    if best is None:
        raise ValueError(f"Could not detect frame interior in {image_path.name}")

    x, y, cw, ch = best

    # Inset to avoid picking up the frame edge
    inset_x = int(cw * inset_frac)
    inset_y = int(ch * inset_frac)
    x1 = x + inset_x
    y1 = y + inset_y
    x2 = x + cw - inset_x
    y2 = y + ch - inset_y

    logger.debug("Detected frame interior in %s: (%d, %d, %d, %d)", image_path.name, x1, y1, x2, y2)
    return (x1, y1, x2, y2)


def _art_orientation(art_path: Path) -> str:
    """Return 'vertical' if portrait, 'horizontal' if landscape."""
    img = Image.open(art_path)
    return "vertical" if img.height >= img.width else "horizontal"


def generate_mockup(
    art_path: Path,
    template_name: str | None = None,
    output_path: Path | None = None,
) -> Path:
    """Composite a sketch image into a frame template mockup.

    Auto-detects the blank frame interior and places the sketch inside it.
    Skips templates whose orientation doesn't match the artwork.

    Args:
        art_path: Path to the processed sketch image.
        template_name: Template key from templates.json. If None, uses first available.
        output_path: Output path for the mockup image.

    Returns:
        Path to the saved mockup image.

    Raises:
        ValueError: If template not found or orientation mismatch.
    """
    art_path = Path(art_path)
    templates = _load_templates()

    if template_name is None:
        template_name = next(iter(templates))

    if template_name not in templates:
        available = ", ".join(templates.keys())
        raise ValueError(f"Unknown template '{template_name}'. Available: {available}")

    meta = templates[template_name]
    art_orient = _art_orientation(art_path)
    tmpl_orient = meta.get("orientation")
    if tmpl_orient and tmpl_orient != art_orient:
        raise ValueError(
            f"Template '{template_name}' is {tmpl_orient}-only, "
            f"but artwork is {art_orient}"
        )

    meta = templates[template_name]
    template_file = TEMPLATE_DIR / meta["file"]
    template_img = Image.open(template_file).convert("RGB")

    # Detect where the blank area is inside the frame
    if "frame_bbox" in meta and meta["frame_bbox"]:
        x1, y1, x2, y2 = meta["frame_bbox"]
    else:
        x1, y1, x2, y2 = _detect_frame_interior(template_file)

    frame_w = x2 - x1
    frame_h = y2 - y1

    # Load and resize the artwork to fill the frame interior
    art = Image.open(art_path).convert("RGB")
    art_ratio = art.width / art.height
    frame_ratio = frame_w / frame_h

    # Fill the frame (crop art edges if aspect ratios differ)
    if art_ratio > frame_ratio:
        # Art is wider — fit height, crop width
        new_h = frame_h
        new_w = int(new_h * art_ratio)
    else:
        # Art is taller — fit width, crop height
        new_w = frame_w
        new_h = int(new_w / art_ratio)

    art_resized = art.resize((new_w, new_h), Image.LANCZOS)

    # Center-crop to exact frame dimensions
    crop_x = (new_w - frame_w) // 2
    crop_y = (new_h - frame_h) // 2
    art_cropped = art_resized.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))

    # Paste the artwork into the template
    result = template_img.copy()
    result.paste(art_cropped, (x1, y1))

    logger.info("Created mockup: %s in %s", art_path.name, template_name)

    # Save output
    if output_path is None:
        output_path = art_path.parent / f"{art_path.stem}_mockup_{template_name}.jpg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(output_path), "JPEG", quality=92)

    logger.info("Mockup saved: %s", output_path)
    return output_path


def generate_all_mockups(
    art_path: Path,
    output_dir: Path | None = None,
) -> list[Path]:
    """Generate mockups for all templates matching the artwork orientation.

    Skips templates whose orientation doesn't match the artwork.
    Returns list of output paths.
    """
    art_path = Path(art_path)
    output_dir = output_dir or art_path.parent
    templates = _load_templates()
    art_orient = _art_orientation(art_path)
    results = []

    for name, meta in templates.items():
        tmpl_orient = meta.get("orientation")
        if tmpl_orient and tmpl_orient != art_orient:
            logger.info("Skipping template '%s' (%s-only, artwork is %s)",
                        name, tmpl_orient, art_orient)
            continue
        out_path = output_dir / f"{art_path.stem}_mockup_{name}.jpg"
        path = generate_mockup(art_path, name, out_path)
        results.append(path)

    return results


def _art_orientation_from_bytes(image_bytes: bytes) -> str:
    """Return 'vertical' if portrait, 'horizontal' if landscape."""
    img = Image.open(io.BytesIO(image_bytes))
    return "vertical" if img.height >= img.width else "horizontal"


def generate_mockup_bytes(
    art_bytes: bytes,
    template_name: str | None = None,
) -> tuple[str, bytes]:
    """Composite a sketch into a frame template, returning JPEG bytes.

    Args:
        art_bytes: Processed sketch image bytes (PNG/JPEG).
        template_name: Template key from templates.json. If None, uses first available.

    Returns:
        Tuple of (template_name, jpeg_bytes).

    Raises:
        ValueError: If template not found or orientation mismatch.
    """
    templates = _load_templates()

    if template_name is None:
        template_name = next(iter(templates))

    if template_name not in templates:
        available = ", ".join(templates.keys())
        raise ValueError(f"Unknown template '{template_name}'. Available: {available}")

    meta = templates[template_name]
    art_orient = _art_orientation_from_bytes(art_bytes)
    tmpl_orient = meta.get("orientation")
    if tmpl_orient and tmpl_orient != art_orient:
        raise ValueError(
            f"Template '{template_name}' is {tmpl_orient}-only, "
            f"but artwork is {art_orient}"
        )

    template_file = TEMPLATE_DIR / meta["file"]
    template_img = Image.open(template_file).convert("RGB")

    if "frame_bbox" in meta and meta["frame_bbox"]:
        x1, y1, x2, y2 = meta["frame_bbox"]
    else:
        x1, y1, x2, y2 = _detect_frame_interior(template_file)

    frame_w = x2 - x1
    frame_h = y2 - y1

    art = Image.open(io.BytesIO(art_bytes)).convert("RGB")
    art_ratio = art.width / art.height
    frame_ratio = frame_w / frame_h

    if art_ratio > frame_ratio:
        new_h = frame_h
        new_w = int(new_h * art_ratio)
    else:
        new_w = frame_w
        new_h = int(new_w / art_ratio)

    art_resized = art.resize((new_w, new_h), Image.LANCZOS)

    crop_x = (new_w - frame_w) // 2
    crop_y = (new_h - frame_h) // 2
    art_cropped = art_resized.crop((crop_x, crop_y, crop_x + frame_w, crop_y + frame_h))

    result = template_img.copy()
    result.paste(art_cropped, (x1, y1))

    buf = io.BytesIO()
    result.save(buf, "JPEG", quality=92)
    data = buf.getvalue()

    logger.info("Created mockup bytes: %s (%.0f KB)", template_name, len(data) / 1024)
    return template_name, data


def generate_all_mockups_bytes(
    art_bytes: bytes,
) -> list[tuple[str, bytes]]:
    """Generate mockups for all matching templates, returning JPEG bytes.

    Skips templates whose orientation doesn't match the artwork.
    Returns list of (template_name, jpeg_bytes) tuples.
    """
    templates = _load_templates()
    art_orient = _art_orientation_from_bytes(art_bytes)
    results = []

    for name, meta in templates.items():
        tmpl_orient = meta.get("orientation")
        if tmpl_orient and tmpl_orient != art_orient:
            logger.info("Skipping template '%s' (%s-only, artwork is %s)",
                        name, tmpl_orient, art_orient)
            continue
        try:
            _, data = generate_mockup_bytes(art_bytes, name)
            results.append((name, data))
        except Exception:
            logger.exception("Mockup generation failed for template '%s'", name)

    return results
