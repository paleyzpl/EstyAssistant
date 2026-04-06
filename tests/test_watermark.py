"""Tests for watermark module."""

import io

import cv2
import numpy as np
from PIL import Image

from etsy_assistant.steps.watermark import apply_watermark


def _make_test_image():
    """Create a simple test image as JPEG bytes."""
    img = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (550, 350), (30, 30, 30), 2)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


class TestApplyWatermark:
    def test_returns_jpeg_bytes(self):
        data = apply_watermark(_make_test_image())
        assert isinstance(data, bytes)
        assert data[:2] == b"\xff\xd8"  # JPEG magic

    def test_output_is_valid_image(self):
        data = apply_watermark(_make_test_image())
        img = Image.open(io.BytesIO(data))
        assert img.size[0] == 600
        assert img.size[1] == 400

    def test_custom_text(self):
        data = apply_watermark(_make_test_image(), text="Test Watermark")
        assert len(data) > 0

    def test_opacity_range(self):
        data_low = apply_watermark(_make_test_image(), opacity=0.05)
        data_high = apply_watermark(_make_test_image(), opacity=0.5)
        # Both should produce valid images
        assert data_low[:2] == b"\xff\xd8"
        assert data_high[:2] == b"\xff\xd8"
