import numpy as np

from etsy_assistant.config import PipelineConfig
from etsy_assistant.steps.perspective import correct_perspective


def test_perspective_disabled():
    image = np.full((500, 500, 3), 200, dtype=np.uint8)
    config = PipelineConfig(perspective_enabled=False)
    result = correct_perspective(image, config)
    np.testing.assert_array_equal(result, image)


def test_perspective_no_quad_returns_image():
    """Image with no clear edges should return without crashing."""
    image = np.full((500, 500, 3), 255, dtype=np.uint8)
    config = PipelineConfig()
    result = correct_perspective(image, config)
    assert result.shape[0] > 0 and result.shape[1] > 0
