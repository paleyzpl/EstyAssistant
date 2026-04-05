import numpy as np
import pytest

from etsy_assistant.config import PipelineConfig
from etsy_assistant.steps.resize import resize_for_print


def test_resize_8x10_portrait():
    image = np.full((4000, 3000), 200, dtype=np.uint8)  # portrait
    config = PipelineConfig()
    result = resize_for_print(image, "8x10", 300, config)
    assert result.shape == (3000, 2400)  # 10" x 8" at 300 DPI


def test_resize_8x10_landscape():
    image = np.full((3000, 4000), 200, dtype=np.uint8)  # landscape
    config = PipelineConfig()
    result = resize_for_print(image, "8x10", 300, config)
    assert result.shape == (2400, 3000)  # 8" x 10" at 300 DPI


def test_resize_none_returns_unchanged():
    image = np.full((500, 400), 200, dtype=np.uint8)
    config = PipelineConfig()
    result = resize_for_print(image, None, 300, config)
    np.testing.assert_array_equal(result, image)


def test_resize_invalid_size():
    image = np.full((500, 400), 200, dtype=np.uint8)
    config = PipelineConfig()
    with pytest.raises(ValueError, match="Unknown size"):
        resize_for_print(image, "3x5", 300, config)


def test_resize_a4():
    image = np.full((4000, 3000), 200, dtype=np.uint8)
    config = PipelineConfig()
    result = resize_for_print(image, "A4", 300, config)
    # A4 at 300 DPI: 2481 x 3507 (portrait orientation)
    assert result.shape[0] == 3507
    assert result.shape[1] == 2481


def test_resize_white_border():
    """Content should be centered on white canvas."""
    image = np.full((100, 200), 0, dtype=np.uint8)  # black, very wide
    config = PipelineConfig()
    result = resize_for_print(image, "8x10", 300, config)
    # Corners should be white (border area)
    assert result[0, 0] == 255
    assert result[-1, -1] == 255
