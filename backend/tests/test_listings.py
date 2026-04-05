"""Tests for listing history endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestSaveListing:
    @patch("api.routes.listings.save_listing")
    def test_save_success(self, mock_save):
        mock_save.return_value = {
            "id": "abc123",
            "title": "Test Sketch",
            "tags": ["ink", "art"],
            "description": "A test.",
            "price": 4.99,
            "s3_key": "uploads/test",
            "sizes": ["8x10"],
            "etsy_listing_id": None,
            "etsy_listing_url": None,
            "preview_url": None,
            "created_at": 1700000000,
        }

        resp = client.post("/listings", json={
            "title": "Test Sketch",
            "tags": ["ink", "art"],
            "description": "A test.",
            "price": 4.99,
            "s3_key": "uploads/test",
            "sizes": ["8x10"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "abc123"
        assert data["title"] == "Test Sketch"
        assert data["tags"] == ["ink", "art"]


class TestListListings:
    @patch("api.routes.listings.list_listings")
    def test_list_success(self, mock_list):
        mock_list.return_value = [
            {
                "id": "abc",
                "title": "Sketch 1",
                "tags": ["art"],
                "description": "Desc.",
                "price": 3.99,
                "s3_key": None,
                "sizes": [],
                "etsy_listing_id": None,
                "etsy_listing_url": None,
                "preview_url": None,
                "created_at": 1700000000,
            },
        ]

        resp = client.get("/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["listings"]) == 1
        assert data["listings"][0]["title"] == "Sketch 1"

    @patch("api.routes.listings.list_listings")
    def test_list_empty(self, mock_list):
        mock_list.return_value = []
        resp = client.get("/listings")
        assert resp.status_code == 200
        assert resp.json()["listings"] == []


class TestGetListing:
    @patch("api.routes.listings.get_listing")
    def test_get_success(self, mock_get):
        mock_get.return_value = {
            "id": "abc",
            "title": "Sketch 1",
            "tags": ["art"],
            "description": "Desc.",
            "price": None,
            "s3_key": None,
            "sizes": [],
            "etsy_listing_id": None,
            "etsy_listing_url": None,
            "preview_url": None,
            "created_at": 1700000000,
        }
        resp = client.get("/listings/abc")
        assert resp.status_code == 200
        assert resp.json()["id"] == "abc"

    @patch("api.routes.listings.get_listing")
    def test_get_not_found(self, mock_get):
        mock_get.return_value = None
        resp = client.get("/listings/nonexistent")
        assert resp.status_code == 404


class TestDeleteListing:
    @patch("api.routes.listings.delete_listing")
    def test_delete_success(self, mock_del):
        mock_del.return_value = True
        resp = client.delete("/listings/abc")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @patch("api.routes.listings.delete_listing")
    def test_delete_not_found(self, mock_del):
        mock_del.return_value = False
        resp = client.delete("/listings/nonexistent")
        assert resp.status_code == 404
