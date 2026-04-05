import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig
from etsy_assistant.steps.autocrop import autocrop


def test_autocrop_removes_border():
    """Sketch with dark border should be cropped to content area."""
    image = np.full((800, 1000, 3), 255, dtype=np.uint8)
    # Draw a solid black rectangle as the sketch content area
    cv2.rectangle(image, (150, 100), (850, 700), (0, 0, 0), -1)
    # Make interior white again (simulating paper with ink border)
    cv2.rectangle(image, (160, 110), (840, 690), (240, 240, 240), -1)
    cv2.line(image, (200, 300), (800, 300), (30, 30, 30), 3)

    config = PipelineConfig(crop_margin_px=10)
    result = autocrop(image, config)

    orig_h, orig_w = image.shape[:2]
    res_h, res_w = result.shape[:2]
    assert res_w < orig_w
    assert res_h < orig_h


def test_autocrop_preserves_content(sketch_on_desk):
    config = PipelineConfig(crop_margin_px=10)
    result = autocrop(sketch_on_desk, config)

    # Should still contain dark ink pixels
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    assert np.min(gray) < 50  # ink lines present


def test_autocrop_no_contours():
    """All-white image should return unchanged."""
    image = np.full((500, 500, 3), 255, dtype=np.uint8)
    config = PipelineConfig()
    result = autocrop(image, config)
    assert result.shape == image.shape


def test_autocrop_small_contour():
    """Tiny dot should be ignored (below 1% area threshold)."""
    image = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    cv2.circle(image, (500, 500), 3, (0, 0, 0), -1)
    config = PipelineConfig()
    result = autocrop(image, config)
    assert result.shape == image.shape
