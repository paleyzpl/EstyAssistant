import cv2
import numpy as np
import pytest


@pytest.fixture
def white_canvas():
    """1000x800 white BGR image."""
    return np.full((800, 1000, 3), 255, dtype=np.uint8)


@pytest.fixture
def sketch_on_desk(white_canvas):
    """Simulate a sketch photo: gray desk with white paper and black ink lines."""
    # Gray desk background
    image = np.full_like(white_canvas, 180)

    # White paper region (offset from edges)
    image[100:700, 150:850] = 240  # slightly off-white paper

    # Draw some "ink" lines on the paper
    cv2.line(image, (200, 200), (800, 200), (30, 30, 30), 3)
    cv2.line(image, (200, 300), (600, 300), (40, 40, 40), 2)
    cv2.rectangle(image, (250, 350), (750, 600), (20, 20, 20), 2)
    cv2.circle(image, (500, 475), 80, (25, 25, 25), 2)

    return image


@pytest.fixture
def grayscale_sketch():
    """Grayscale image with faint lines on slightly gray background."""
    image = np.full((600, 800), 220, dtype=np.uint8)
    cv2.line(image, (100, 100), (700, 100), 60, 3)
    cv2.line(image, (100, 200), (500, 200), 80, 2)
    cv2.rectangle(image, (150, 250), (650, 500), 40, 2)
    return image
