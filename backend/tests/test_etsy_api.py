import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from etsy_assistant.etsy_api import (
    EtsyCredentials,
    DraftListing,
    _generate_pkce,
    create_draft_listing,
    refresh_access_token,
    upload_listing_file,
    upload_listing_image,
)


@pytest.fixture
def creds():
    return EtsyCredentials(
        api_key="test_api_key",
        access_token="12345.test_token",
        refresh_token="test_refresh",
        user_id="12345",
        shop_id="67890",
    )


@pytest.fixture
def sample_image(tmp_path):
    img_path = tmp_path / "sketch.png"
    img = Image.fromarray(np.full((100, 100, 3), 255, dtype=np.uint8))
    img.save(str(img_path))
    return img_path


@pytest.fixture
def small_file(tmp_path):
    f = tmp_path / "download.png"
    img = Image.fromarray(np.full((100, 100, 3), 255, dtype=np.uint8))
    img.save(str(f))
    return f


class TestEtsyCredentials:
    def test_save_and_load(self, tmp_path, creds):
        path = tmp_path / "creds.json"
        creds.save(path)

        assert path.exists()
        assert oct(path.stat().st_mode)[-3:] == "600"

        loaded = EtsyCredentials.load(path)
        assert loaded.api_key == creds.api_key
        assert loaded.access_token == creds.access_token
        assert loaded.refresh_token == creds.refresh_token
        assert loaded.user_id == creds.user_id
        assert loaded.shop_id == creds.shop_id

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No credentials found"):
            EtsyCredentials.load(tmp_path / "nonexistent.json")

    def test_save_creates_parent_dirs(self, tmp_path, creds):
        path = tmp_path / "sub" / "dir" / "creds.json"
        creds.save(path)
        assert path.exists()


class TestPKCE:
    def test_generates_verifier_and_challenge(self):
        verifier, challenge = _generate_pkce()
        assert len(verifier) >= 43
        assert len(verifier) <= 128
        assert len(challenge) > 0
        # Challenge should be base64url encoded (no +, /, or =)
        assert "+" not in challenge
        assert "/" not in challenge
        assert "=" not in challenge

    def test_different_each_call(self):
        v1, c1 = _generate_pkce()
        v2, c2 = _generate_pkce()
        assert v1 != v2
        assert c1 != c2


class TestCreateDraftListing:
    def test_creates_listing(self, creds):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "listing_id": 111222333,
            "url": "https://www.etsy.com/listing/111222333",
        }

        with patch("etsy_assistant.etsy_api._request_with_refresh", return_value=mock_resp) as mock_req:
            result = create_draft_listing(
                creds=creds,
                title="Test Pen Ink Print",
                description="A beautiful sketch.",
                tags=["pen ink", "wall art"],
                price=12.99,
            )

            assert isinstance(result, DraftListing)
            assert result.listing_id == "111222333"
            assert result.title == "Test Pen Ink Print"
            assert result.url == "https://www.etsy.com/listing/111222333"

            call_kwargs = mock_req.call_args
            data = call_kwargs.kwargs["data"]
            assert data["type"] == "download"
            assert data["quantity"] == 999999
            assert data["who_made"] == "i_did"
            assert data["price"] == 12.99

    def test_raises_without_shop_id(self):
        creds = EtsyCredentials(
            api_key="key", access_token="token",
            refresh_token="refresh", user_id="123",
            shop_id=None,
        )
        with pytest.raises(ValueError, match="No shop_id"):
            create_draft_listing(creds, "Title", "Desc", ["tag"], 10.0)

    def test_truncates_title_and_tags(self, creds):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"listing_id": 1, "url": None}

        with patch("etsy_assistant.etsy_api._request_with_refresh", return_value=mock_resp) as mock_req:
            create_draft_listing(
                creds=creds,
                title="A" * 200,
                description="desc",
                tags=[f"tag{i}" for i in range(20)],
                price=5.0,
            )
            data = mock_req.call_args.kwargs["data"]
            assert len(data["title"]) == 140
            assert len(data["tags"].split(",")) == 13


class TestUploadListingImage:
    def test_uploads_image(self, creds, sample_image):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"listing_image_id": 999}

        with patch("etsy_assistant.etsy_api._request_with_refresh", return_value=mock_resp):
            image_id = upload_listing_image(creds, "111", sample_image)
            assert image_id == "999"

    def test_raises_without_shop_id(self, sample_image):
        creds = EtsyCredentials(
            api_key="key", access_token="token",
            refresh_token="refresh", user_id="123",
        )
        with pytest.raises(ValueError, match="No shop_id"):
            upload_listing_image(creds, "111", sample_image)


class TestUploadListingFile:
    def test_uploads_file(self, creds, small_file):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"listing_file_id": 888}

        with patch("etsy_assistant.etsy_api._request_with_refresh", return_value=mock_resp):
            file_id = upload_listing_file(creds, "111", small_file)
            assert file_id == "888"

    def test_rejects_large_file(self, creds, tmp_path):
        large_file = tmp_path / "huge.png"
        # Create a file just over 20MB
        large_file.write_bytes(b"\x00" * (21 * 1024 * 1024))

        with pytest.raises(ValueError, match="too large"):
            upload_listing_file(creds, "111", large_file)


class TestRefreshToken:
    def test_refreshes_token(self, creds):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "12345.new_token",
            "refresh_token": "new_refresh",
        }

        with patch("etsy_assistant.etsy_api.httpx.Client") as mock_client_cls:
            mock_http = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.post.return_value = mock_resp

            new_creds = refresh_access_token(creds)
            assert new_creds.access_token == "12345.new_token"
            assert new_creds.refresh_token == "new_refresh"
            assert new_creds.shop_id == creds.shop_id
