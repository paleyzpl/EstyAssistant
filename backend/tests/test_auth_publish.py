"""Tests for Etsy auth and publish endpoints."""

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture
def sketch_png_bytes():
    image = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (500, 350), (30, 30, 30), 2)
    _, buf = cv2.imencode(".png", image)
    return buf.tobytes()


class TestAuthStatus:
    @patch("api.routes.auth.load_credentials")
    def test_not_connected(self, mock_load):
        mock_load.return_value = None
        resp = client.get("/auth/etsy/status")
        assert resp.status_code == 200
        assert resp.json() == {"connected": False, "shop_id": None}

    @patch("api.routes.auth.load_credentials")
    def test_connected(self, mock_load):
        mock_load.return_value = {
            "api_key": "key",
            "access_token": "tok",
            "refresh_token": "ref",
            "user_id": "123",
            "shop_id": "456",
        }
        resp = client.get("/auth/etsy/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["shop_id"] == "456"


class TestAuthStart:
    @patch("api.routes.auth.save_oauth_state")
    @patch("api.routes.auth.build_auth_url")
    @patch("api.routes.auth.ETSY_API_KEY", "test-key")
    def test_returns_auth_url(self, mock_build, mock_save):
        mock_build.return_value = ("https://etsy.com/oauth?...", "state123", "verifier123")
        resp = client.get("/auth/etsy/start")
        assert resp.status_code == 200
        assert "auth_url" in resp.json()
        mock_save.assert_called_once()

    @patch("api.routes.auth.ETSY_API_KEY", "")
    def test_missing_api_key(self):
        resp = client.get("/auth/etsy/start")
        assert resp.status_code == 500


class TestAuthCallback:
    @patch("api.routes.auth.save_credentials")
    @patch("api.routes.auth.exchange_code")
    @patch("api.routes.auth.load_oauth_state")
    @patch("api.routes.auth.ETSY_API_KEY", "test-key")
    def test_successful_callback(self, mock_state, mock_exchange, mock_save):
        mock_state.return_value = {"verifier": "v123", "redirect_uri": "http://localhost/cb"}
        mock_creds = MagicMock()
        mock_creds.api_key = "key"
        mock_creds.access_token = "tok"
        mock_creds.refresh_token = "ref"
        mock_creds.user_id = "123"
        mock_creds.shop_id = "456"
        mock_exchange.return_value = mock_creds

        resp = client.post("/auth/etsy/callback?code=authcode&state=state123")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @patch("api.routes.auth.load_oauth_state")
    @patch("api.routes.auth.ETSY_API_KEY", "test-key")
    def test_invalid_state(self, mock_state):
        mock_state.return_value = None
        resp = client.post("/auth/etsy/callback?code=authcode&state=bad")
        assert resp.status_code == 400


class TestAuthDisconnect:
    @patch("api.routes.auth.delete_credentials")
    def test_disconnect(self, mock_delete):
        resp = client.post("/auth/etsy/disconnect")
        assert resp.status_code == 200
        mock_delete.assert_called_once()


class TestPublish:
    @patch("api.routes.publish.update_job")
    @patch("api.routes.publish.create_job")
    @patch("api.routes.publish.upload_listing_file_bytes")
    @patch("api.routes.publish.upload_listing_image_bytes")
    @patch("api.routes.publish.create_draft_listing")
    @patch("api.routes.publish.process_image_bytes")
    @patch("api.routes.publish.read_image")
    @patch("api.routes.publish.load_credentials")
    def test_publish_success(self, mock_creds, mock_read, mock_process,
                             mock_create, mock_upload_img, mock_upload_file,
                             mock_create_job, mock_update_job, sketch_png_bytes):
        mock_creds.return_value = {
            "api_key": "key", "access_token": "tok",
            "refresh_token": "ref", "user_id": "123", "shop_id": "456",
        }
        mock_read.return_value = sketch_png_bytes
        mock_process.return_value = [("8x10", b"\x89PNGfakedata")]
        mock_draft = MagicMock()
        mock_draft.listing_id = "999"
        mock_draft.url = "https://etsy.com/listing/999"
        mock_draft.title = "Test Listing"
        mock_create.return_value = mock_draft
        mock_upload_img.return_value = "img1"
        mock_upload_file.return_value = "file1"

        resp = client.post("/publish", json={
            "s3_key": "uploads/test",
            "sizes": ["8x10"],
            "title": "Test Listing",
            "description": "A test.",
            "tags": ["test"],
            "price": 4.99,
        })
        assert resp.status_code == 200
        assert "job_id" in resp.json()

    @patch("api.routes.publish.load_credentials")
    def test_publish_not_connected(self, mock_creds):
        mock_creds.return_value = None
        resp = client.post("/publish", json={
            "s3_key": "uploads/test",
            "sizes": ["8x10"],
            "title": "Test",
            "description": "Test",
            "tags": ["test"],
            "price": 4.99,
        })
        assert resp.status_code == 401


class TestJobStatus:
    @patch("api.routes.publish.get_job")
    def test_job_found(self, mock_get):
        mock_get.return_value = {"status": "completed", "result": {"listing_id": "999"}}
        resp = client.get("/jobs/abc123")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @patch("api.routes.publish.get_job")
    def test_job_not_found(self, mock_get):
        mock_get.return_value = None
        resp = client.get("/jobs/nonexistent")
        assert resp.status_code == 404
