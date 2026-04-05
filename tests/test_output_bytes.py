"""Tests for encode_output and _to_pil functions."""

import numpy as np
from PIL import Image
import io

from etsy_assistant.steps.output import _to_pil, encode_output


class TestToPil:
    def test_bgr_to_rgb(self):
        # Create a BGR image: blue pixel
        bgr = np.zeros((10, 10, 3), dtype=np.uint8)
        bgr[:, :, 0] = 255  # Blue channel in BGR
        pil = _to_pil(bgr)
        assert pil.mode == "RGB"
        # After conversion, the red channel should be 0 and blue should be 255
        r, g, b = pil.getpixel((0, 0))
        assert r == 0 and b == 255

    def test_grayscale(self):
        gray = np.full((10, 10), 128, dtype=np.uint8)
        pil = _to_pil(gray)
        assert pil.mode == "L"
        assert pil.getpixel((0, 0)) == 128


class TestEncodeOutput:
    def test_returns_png_bytes(self):
        image = np.full((100, 100, 3), 200, dtype=np.uint8)
        data = encode_output(image)
        assert isinstance(data, bytes)
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_returns_jpeg_bytes(self):
        image = np.full((100, 100, 3), 200, dtype=np.uint8)
        data = encode_output(image, fmt="JPEG")
        assert isinstance(data, bytes)
        assert data[:2] == b"\xff\xd8"

    def test_dpi_metadata(self):
        image = np.full((100, 100, 3), 200, dtype=np.uint8)
        data = encode_output(image, dpi=300)
        pil = Image.open(io.BytesIO(data))
        dpi = pil.info.get("dpi", (72, 72))
        assert abs(dpi[0] - 300) < 1 and abs(dpi[1] - 300) < 1

    def test_grayscale_encoding(self):
        gray = np.full((50, 50), 180, dtype=np.uint8)
        data = encode_output(gray)
        assert isinstance(data, bytes)
        assert len(data) > 0
