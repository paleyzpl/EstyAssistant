import numpy as np
import cv2
import pytest
from pathlib import Path

from etsy_assistant.config import PipelineConfig
from etsy_assistant.pipeline import process_image


@pytest.fixture
def sample_input(tmp_path):
    """Create a synthetic sketch photo and save as JPEG."""
    image = np.full((800, 1000, 3), 180, dtype=np.uint8)
    image[100:700, 150:850] = 235
    cv2.line(image, (200, 200), (800, 200), (30, 30, 30), 3)
    cv2.rectangle(image, (250, 350), (750, 600), (20, 20, 20), 2)
    cv2.circle(image, (500, 475), 80, (25, 25, 25), 2)

    path = tmp_path / "test_sketch.jpg"
    cv2.imwrite(str(path), image)
    return path


def test_full_pipeline(sample_input, tmp_path):
    output_path = tmp_path / "output.png"
    results = process_image(sample_input, output_path)
    assert len(results) == 1
    assert results[0].exists()
    assert results[0].stat().st_size > 0


def test_pipeline_multiple_sizes(sample_input, tmp_path):
    output_dir = tmp_path / "output"
    results = process_image(sample_input, output_dir, sizes=["8x10", "5x7"])
    assert len(results) == 2
    for path in results:
        assert path.exists()
        assert "8x10" in path.name or "5x7" in path.name


def test_pipeline_skip_steps(sample_input, tmp_path):
    output_path = tmp_path / "output.png"
    results = process_image(
        sample_input, output_path,
        skip_steps={"perspective", "contrast"},
    )
    assert len(results) == 1
    assert results[0].exists()


def test_pipeline_debug_mode(sample_input, tmp_path):
    output_path = tmp_path / "output.png"
    process_image(sample_input, output_path, debug=True)
    debug_dir = sample_input.parent / "debug"
    assert debug_dir.exists()
    debug_files = list(debug_dir.glob("*.png"))
    assert len(debug_files) >= 3  # original + at least 2 steps


def test_pipeline_bad_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        process_image(tmp_path / "nonexistent.jpg", tmp_path / "out.png")
