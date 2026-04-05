import numpy as np

from etsy_assistant.config import PipelineConfig
from etsy_assistant.steps.background import cleanup_background


def test_background_whitens_paper(grayscale_sketch):
    config = PipelineConfig()
    result = cleanup_background(grayscale_sketch, config)

    # Background pixels should be pushed to white
    assert np.mean(result) > 240


def test_background_preserves_ink(grayscale_sketch):
    config = PipelineConfig()
    result = cleanup_background(grayscale_sketch, config)

    # Should still have dark pixels (ink lines)
    assert np.min(result) < 100


def test_background_bgr_input(sketch_on_desk):
    """Should handle BGR input (converts to grayscale)."""
    config = PipelineConfig()
    result = cleanup_background(sketch_on_desk, config)
    assert len(result.shape) == 2  # output is grayscale
