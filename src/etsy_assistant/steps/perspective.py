import logging

import cv2
import numpy as np

from etsy_assistant.config import PipelineConfig

logger = logging.getLogger(__name__)


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left has smallest sum
    rect[2] = pts[np.argmax(s)]  # bottom-right has largest sum
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]  # top-right has smallest difference
    rect[3] = pts[np.argmax(d)]  # bottom-left has largest difference
    return rect


def _perspective_transform(image: np.ndarray, contour: np.ndarray) -> np.ndarray | None:
    """Attempt 4-point perspective correction from a quadrilateral contour."""
    peri = cv2.arcLength(contour, True)
    for eps_mult in [0.02, 0.03, 0.05, 0.08]:
        approx = cv2.approxPolyDP(contour, eps_mult * peri, True)
        if len(approx) == 4:
            src_pts = _order_points(approx.reshape(4, 2).astype(np.float32))

            widths = [np.linalg.norm(src_pts[1] - src_pts[0]),
                      np.linalg.norm(src_pts[2] - src_pts[3])]
            heights = [np.linalg.norm(src_pts[3] - src_pts[0]),
                       np.linalg.norm(src_pts[2] - src_pts[1])]
            w = int(max(widths))
            h = int(max(heights))

            dst_pts = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
            matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            return cv2.warpPerspective(image, matrix, (w, h), borderValue=(255, 255, 255))
    return None


def _rotation_deskew(image: np.ndarray, config: PipelineConfig) -> np.ndarray:
    """Fallback: detect dominant angle via Hough lines and rotate to correct."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
    edges = cv2.Canny(gray, 50, 150)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=config.hough_threshold,
        minLineLength=config.hough_min_line_length,
        maxLineGap=config.hough_max_line_gap,
    )
    if lines is None or len(lines) == 0:
        logger.info("No lines detected, skipping deskew")
        return image

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Only consider near-horizontal or near-vertical lines
        if abs(angle) < 45:
            angles.append(angle)
        elif abs(angle - 90) < 45 or abs(angle + 90) < 45:
            angles.append(angle - 90 if angle > 0 else angle + 90)

    if not angles:
        logger.info("No usable line angles, skipping deskew")
        return image

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        logger.info("Skew angle %.2f° too small, skipping", median_angle)
        return image

    logger.info("Rotating by %.2f° to correct skew", -median_angle)
    h, w = image.shape[:2]
    center = (w / 2, h / 2)
    matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)

    cos_a = abs(matrix[0, 0])
    sin_a = abs(matrix[0, 1])
    new_w = int(h * sin_a + w * cos_a)
    new_h = int(h * cos_a + w * sin_a)
    matrix[0, 2] += (new_w - w) / 2
    matrix[1, 2] += (new_h - h) / 2

    return cv2.warpAffine(image, matrix, (new_w, new_h), borderValue=(255, 255, 255))


def correct_perspective(image: np.ndarray, config: PipelineConfig) -> np.ndarray:
    """Correct perspective distortion or rotation from angled phone photos."""
    if not config.perspective_enabled:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest = max(contours, key=cv2.contourArea)
        result = _perspective_transform(image, largest)
        if result is not None:
            logger.info("Applied 4-point perspective correction")
            return result

    logger.info("No quadrilateral found, falling back to rotation deskew")
    return _rotation_deskew(image, config)
