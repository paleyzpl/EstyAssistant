import numpy as np

from etsy_assistant.config import PipelineConfig
from etsy_assistant.steps.contrast import enhance_contrast


def test_contrast_darkens_ink(grayscale_sketch):
    config = PipelineConfig()
    result = enhance_contrast(grayscale_sketch, config)

    # Dark lines should be darker after enhancement
    assert np.min(result) < np.min(grayscale_sketch)


def test_contrast_output_full_range(grayscale_sketch):
    config = PipelineConfig()
    result = enhance_contrast(grayscale_sketch, config)

    # Should use more of the dynamic range
    assert np.max(result) >= 250
    assert np.min(result) <= 20
