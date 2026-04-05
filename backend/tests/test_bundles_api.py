"""Tests for bundle generation API endpoint."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


SAMPLE_LISTINGS = [
    {
        "title": "Vintage Trolley Sketch",
        "tags": ["trolley", "urban art", "pen ink", "city sketch", "digital download"],
        "description": "A trolley sketch.",
        "price": 4.99,
    },
    {
        "title": "City Bridge Drawing",
        "tags": ["bridge", "urban art", "pen ink", "city sketch", "digital download"],
        "description": "A bridge drawing.",
        "price": 4.99,
    },
    {
        "title": "Downtown Skyline Sketch",
        "tags": ["skyline", "urban art", "pen ink", "city sketch", "digital download"],
        "description": "A skyline sketch.",
        "price": 4.99,
    },
]


class TestBundleGenerate:
    def test_generates_bundles(self):
        resp = client.post("/bundles/generate", json={
            "listings": SAMPLE_LISTINGS,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bundles"]) >= 1
        bundle = data["bundles"][0]
        assert bundle["pack_size"] == 3
        assert len(bundle["title"]) <= 140
        assert len(bundle["tags"]) <= 13
        assert bundle["price"] > 0

    def test_with_explicit_groups(self):
        resp = client.post("/bundles/generate", json={
            "listings": SAMPLE_LISTINGS,
            "groups": [{"theme": "Urban Art", "indices": [0, 1, 2]}],
        })
        assert resp.status_code == 200
        bundles = resp.json()["bundles"]
        assert len(bundles) == 1
        assert bundles[0]["theme"] == "Urban Art"

    def test_too_few_listings(self):
        resp = client.post("/bundles/generate", json={
            "listings": SAMPLE_LISTINGS[:2],
        })
        assert resp.status_code == 400

    def test_bundle_has_discount(self):
        resp = client.post("/bundles/generate", json={
            "listings": SAMPLE_LISTINGS,
            "groups": [{"theme": "Test", "indices": [0, 1, 2]}],
        })
        bundle = resp.json()["bundles"][0]
        # 3-pack at 25% discount: 4.99 * 3 * 0.75 = 11.23
        assert bundle["price"] == round(4.99 * 3 * 0.75, 2)

    def test_bundle_tags_include_bundle_specific(self):
        resp = client.post("/bundles/generate", json={
            "listings": SAMPLE_LISTINGS,
            "groups": [{"theme": "Test", "indices": [0, 1, 2]}],
        })
        tags = resp.json()["bundles"][0]["tags"]
        assert "3 pack prints" in tags
        assert "art bundle" in tags
