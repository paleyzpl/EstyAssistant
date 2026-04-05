"""Tests for FastAPI backend endpoints."""

import json
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture
def sketch_png_bytes():
    """Create a synthetic sketch and encode as PNG bytes."""
    image = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.line(image, (50, 50), (550, 50), (20, 20, 20), 2)
    cv2.rectangle(image, (100, 100), (500, 350), (30, 30, 30), 2)
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestUploadUrlEndpoint:
    @patch("api.routes.upload.generate_upload_url")
    def test_returns_upload_url(self, mock_gen):
        mock_gen.return_value = ("https://s3.example.com/upload", "uploads/abc123")
        resp = client.get("/upload-url")
        assert resp.status_code == 200
        data = resp.json()
        assert data["upload_url"] == "https://s3.example.com/upload"
        assert data["s3_key"] == "uploads/abc123"

    @patch("api.routes.upload.generate_upload_url")
    def test_passes_content_type(self, mock_gen):
        mock_gen.return_value = ("https://s3.example.com/upload", "uploads/abc")
        client.get("/upload-url?content_type=image/png")
        mock_gen.assert_called_once_with("image/png")

    @patch("api.routes.upload.generate_upload_url")
    def test_default_content_type(self, mock_gen):
        mock_gen.return_value = ("https://s3.example.com/upload", "uploads/abc")
        client.get("/upload-url")
        mock_gen.assert_called_once_with("image/jpeg")


class TestProcessEndpoint:
    @patch("api.routes.process.write_image")
    @patch("api.routes.process.read_image")
    def test_process_success(self, mock_read, mock_write, sketch_png_bytes):
        mock_read.return_value = sketch_png_bytes
        mock_write.return_value = "https://s3.example.com/processed/abc/8x10.png"

        resp = client.post("/process", json={
            "s3_key": "uploads/test123",
            "sizes": ["8x10"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["preview_url"] != ""
        assert len(data["outputs"]) == 1
        assert data["outputs"][0]["size"] == "8x10"

    @patch("api.routes.process.write_image")
    @patch("api.routes.process.read_image")
    def test_process_multiple_sizes(self, mock_read, mock_write, sketch_png_bytes):
        mock_read.return_value = sketch_png_bytes
        mock_write.return_value = "https://s3.example.com/processed/abc/out.png"

        resp = client.post("/process", json={
            "s3_key": "uploads/test123",
            "sizes": ["8x10", "5x7"],
        })
        assert resp.status_code == 200
        assert len(resp.json()["outputs"]) == 2

    @patch("api.routes.process.read_image")
    def test_process_image_not_found(self, mock_read):
        mock_read.side_effect = Exception("NoSuchKey")

        resp = client.post("/process", json={
            "s3_key": "uploads/nonexistent",
            "sizes": ["8x10"],
        })
        assert resp.status_code == 404

    @patch("api.routes.process.write_image")
    @patch("api.routes.process.read_image")
    def test_process_writes_to_s3(self, mock_read, mock_write, sketch_png_bytes):
        mock_read.return_value = sketch_png_bytes
        mock_write.return_value = "https://s3.example.com/out.png"

        client.post("/process", json={
            "s3_key": "uploads/test123",
            "sizes": ["8x10"],
        })
        # Should have written at least one processed image to S3
        assert mock_write.call_count == 1
        call_args = mock_write.call_args
        assert call_args[0][0].startswith("processed/")
        assert isinstance(call_args[0][1], bytes)


class TestListingGenerateEndpoint:
    @patch("api.routes.listing.generate_listing_from_bytes")
    @patch("api.routes.listing.read_image")
    def test_generate_success(self, mock_read, mock_gen, sketch_png_bytes):
        mock_read.return_value = sketch_png_bytes
        mock_listing = MagicMock()
        mock_listing.title = "Test Ink Sketch | Wall Art"
        mock_listing.tags = ["ink sketch", "wall art"]
        mock_listing.description = "A test description."
        mock_gen.return_value = mock_listing

        resp = client.post("/listing/generate", json={
            "s3_key": "processed/abc/8x10.png",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Ink Sketch | Wall Art"
        assert data["tags"] == ["ink sketch", "wall art"]
        assert data["description"] == "A test description."

    @patch("api.routes.listing.read_image")
    def test_generate_image_not_found(self, mock_read):
        mock_read.side_effect = Exception("NoSuchKey")

        resp = client.post("/listing/generate", json={
            "s3_key": "processed/nonexistent",
        })
        assert resp.status_code == 404

    @patch("api.routes.listing.generate_listing_from_bytes")
    @patch("api.routes.listing.read_image")
    def test_generate_api_failure(self, mock_read, mock_gen, sketch_png_bytes):
        mock_read.return_value = sketch_png_bytes
        mock_gen.side_effect = ValueError("API error")

        resp = client.post("/listing/generate", json={
            "s3_key": "processed/abc/8x10.png",
        })
        assert resp.status_code == 500
