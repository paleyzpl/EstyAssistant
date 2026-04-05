"""Tests for bytes-based mockup generation functions."""

import io

import cv2
import numpy as np
import pytest
from PIL import Image

from etsy_assistant.steps.mockup import (
    _art_orientation_from_bytes,
    generate_all_mockups_bytes,
    generate_mockup_bytes,
    list_templates,
)


@pytest.fixture
def portrait_png_bytes():
    """Create a portrait-oriented (vertical) sketch as PNG bytes."""
    image = np.full((800, 600, 3), 240, dtype=np.uint8)
    cv2.line(image, (50, 50), (550, 50), (20, 20, 20), 2)
    cv2.rectangle(image, (100, 100), (500, 700), (30, 30, 30), 2)
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


@pytest.fixture
def landscape_png_bytes():
    """Create a landscape-oriented (horizontal) sketch as PNG bytes."""
    image = np.full((400, 800, 3), 240, dtype=np.uint8)
    cv2.line(image, (50, 50), (750, 50), (20, 20, 20), 2)
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


class TestArtOrientationFromBytes:
    def test_portrait(self, portrait_png_bytes):
        assert _art_orientation_from_bytes(portrait_png_bytes) == "vertical"

    def test_landscape(self, landscape_png_bytes):
        assert _art_orientation_from_bytes(landscape_png_bytes) == "horizontal"


class TestGenerateMockupBytes:
    def test_returns_jpeg_bytes(self, portrait_png_bytes):
        templates = list_templates()
        if not templates:
            pytest.skip("No templates available")
        name, data = generate_mockup_bytes(portrait_png_bytes)
        assert isinstance(data, bytes)
        # JPEG magic bytes
        assert data[:2] == b"\xff\xd8"
        assert isinstance(name, str)

    def test_specific_template(self, portrait_png_bytes):
        templates = list_templates()
        if not templates:
            pytest.skip("No templates available")
        name, data = generate_mockup_bytes(portrait_png_bytes, templates[0])
        assert name == templates[0]
        assert len(data) > 0

    def test_unknown_template_raises(self, portrait_png_bytes):
        with pytest.raises(ValueError, match="Unknown template"):
            generate_mockup_bytes(portrait_png_bytes, "nonexistent_template")

    def test_orientation_mismatch_raises(self, landscape_png_bytes):
        # All current templates are vertical; landscape art should fail
        templates = list_templates()
        if not templates:
            pytest.skip("No templates available")
        with pytest.raises(ValueError, match="only"):
            generate_mockup_bytes(landscape_png_bytes, templates[0])


class TestGenerateAllMockupsBytes:
    def test_returns_matching_mockups(self, portrait_png_bytes):
        results = generate_all_mockups_bytes(portrait_png_bytes)
        assert isinstance(results, list)
        # Should have at least one mockup for portrait art
        assert len(results) >= 1
        for name, data in results:
            assert isinstance(name, str)
            assert data[:2] == b"\xff\xd8"

    def test_skips_mismatched_orientation(self, landscape_png_bytes):
        # All templates are vertical, landscape art should get no matches
        results = generate_all_mockups_bytes(landscape_png_bytes)
        assert len(results) == 0
