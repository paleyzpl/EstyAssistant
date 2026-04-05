"""Tests for bytes-based pipeline functions (used by web API)."""

import cv2
import numpy as np
import pytest

from etsy_assistant.config import PipelineConfig
from etsy_assistant.pipeline import (
    _decode_image,
    process_image_bytes,
    run_pipeline,
)


@pytest.fixture
def sketch_jpeg_bytes():
    """Create a synthetic sketch photo and encode as JPEG bytes."""
    image = np.full((800, 1000, 3), 180, dtype=np.uint8)
    image[100:700, 150:850] = 235
    cv2.line(image, (200, 200), (800, 200), (30, 30, 30), 3)
    cv2.rectangle(image, (250, 350), (750, 600), (20, 20, 20), 2)
    cv2.circle(image, (500, 475), 80, (25, 25, 25), 2)
    _, buf = cv2.imencode(".jpg", image)
    return buf.tobytes()


@pytest.fixture
def sketch_png_bytes():
    """Create a synthetic sketch and encode as PNG bytes."""
    image = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.line(image, (50, 50), (550, 50), (20, 20, 20), 2)
    cv2.rectangle(image, (100, 100), (500, 350), (30, 30, 30), 2)
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


class TestDecodeImage:
    def test_decodes_jpeg(self, sketch_jpeg_bytes):
        image = _decode_image(sketch_jpeg_bytes)
        assert isinstance(image, np.ndarray)
        assert image.shape == (800, 1000, 3)

    def test_decodes_png(self, sketch_png_bytes):
        image = _decode_image(sketch_png_bytes)
        assert isinstance(image, np.ndarray)
        assert image.shape == (400, 600, 3)

    def test_raises_on_invalid_bytes(self):
        with pytest.raises(ValueError, match="Could not decode"):
            _decode_image(b"not an image")

    def test_raises_on_empty_bytes(self):
        with pytest.raises((ValueError, cv2.error)):
            _decode_image(b"")


class TestRunPipeline:
    def test_returns_processed_image(self, sketch_on_desk):
        result = run_pipeline(sketch_on_desk)
        assert isinstance(result, np.ndarray)
        assert result.shape[0] > 0 and result.shape[1] > 0

    def test_default_config(self, sketch_on_desk):
        result = run_pipeline(sketch_on_desk, config=None)
        assert isinstance(result, np.ndarray)

    def test_skip_steps(self, sketch_on_desk):
        result = run_pipeline(
            sketch_on_desk, skip_steps={"autocrop", "perspective", "background", "contrast"}
        )
        # Skipping all steps should return the original image
        np.testing.assert_array_equal(result, sketch_on_desk)

    def test_skip_some_steps(self, sketch_on_desk):
        result = run_pipeline(sketch_on_desk, skip_steps={"perspective", "contrast"})
        assert isinstance(result, np.ndarray)


class TestProcessImageBytes:
    def test_default_size(self, sketch_jpeg_bytes):
        results = process_image_bytes(sketch_jpeg_bytes)
        assert len(results) == 1
        label, data = results[0]
        assert label == "default"
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_single_size(self, sketch_jpeg_bytes):
        results = process_image_bytes(sketch_jpeg_bytes, sizes=["8x10"])
        assert len(results) == 1
        assert results[0][0] == "8x10"
        assert len(results[0][1]) > 0

    def test_multiple_sizes(self, sketch_jpeg_bytes):
        results = process_image_bytes(sketch_jpeg_bytes, sizes=["8x10", "5x7"])
        assert len(results) == 2
        labels = [r[0] for r in results]
        assert "8x10" in labels
        assert "5x7" in labels

    def test_skip_steps(self, sketch_jpeg_bytes):
        results = process_image_bytes(
            sketch_jpeg_bytes, sizes=["8x10"], skip_steps={"perspective"}
        )
        assert len(results) == 1
        assert len(results[0][1]) > 0

    def test_invalid_bytes_raises(self):
        with pytest.raises(ValueError):
            process_image_bytes(b"not an image")

    def test_output_is_valid_png(self, sketch_jpeg_bytes):
        results = process_image_bytes(sketch_jpeg_bytes)
        _, data = results[0]
        # PNG magic bytes
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
