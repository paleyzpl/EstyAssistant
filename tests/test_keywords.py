import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from etsy_assistant.steps.keywords import (
    ListingMetadata,
    _encode_image,
    _encode_image_bytes,
    _parse_response,
    generate_listing,
    generate_listing_from_bytes,
    load_metadata,
    save_metadata,
)


@pytest.fixture
def sample_image(tmp_path):
    """Create a minimal PNG image for testing."""
    img_path = tmp_path / "sketch.png"
    img = Image.fromarray(np.full((100, 100, 3), 255, dtype=np.uint8))
    img.save(str(img_path))
    return img_path


@pytest.fixture
def sample_jpeg(tmp_path):
    """Create a minimal JPEG image for testing."""
    img_path = tmp_path / "sketch.jpg"
    img = Image.fromarray(np.full((100, 100, 3), 255, dtype=np.uint8))
    img.save(str(img_path))
    return img_path


@pytest.fixture
def valid_api_response():
    return json.dumps({
        "title": "Minimalist City Skyline Pen Ink Drawing - Printable Wall Art Digital Download",
        "tags": [
            "pen ink drawing",
            "city skyline art",
            "minimalist print",
            "wall art download",
            "urban sketch",
            "line drawing",
            "printable art",
            "home decor print",
            "architecture art",
            "black white art",
            "digital download",
            "modern wall art",
            "office decor",
        ],
        "description": "A beautiful pen and ink sketch of a city skyline. "
        "This minimalist artwork features clean lines and architectural detail. "
        "Perfect for modern home decor, office spaces, or as a thoughtful gift. "
        "Print at home or at your local print shop for instant wall art.",
    })


class TestEncodeImage:
    def test_encodes_png(self, sample_image):
        data, media_type = _encode_image(sample_image)
        assert media_type == "image/png"
        assert len(data) > 0

    def test_encodes_jpeg(self, sample_jpeg):
        data, media_type = _encode_image(sample_jpeg)
        assert media_type == "image/jpeg"
        assert len(data) > 0

    def test_unknown_extension_defaults_to_png(self, tmp_path):
        img_path = tmp_path / "sketch.bmp"
        img = Image.fromarray(np.full((10, 10, 3), 255, dtype=np.uint8))
        img.save(str(img_path))
        _, media_type = _encode_image(img_path)
        assert media_type == "image/png"


class TestParseResponse:
    def test_parses_plain_json(self, valid_api_response):
        result = _parse_response(valid_api_response)
        assert result["title"].startswith("Minimalist")
        assert len(result["tags"]) == 13

    def test_parses_fenced_json(self, valid_api_response):
        fenced = f"```json\n{valid_api_response}\n```"
        result = _parse_response(fenced)
        assert "title" in result
        assert "tags" in result

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_response("not json at all")

    def test_handles_whitespace(self, valid_api_response):
        result = _parse_response(f"  \n{valid_api_response}\n  ")
        assert "title" in result


class TestGenerateListing:
    def test_returns_listing_metadata(self, sample_image, valid_api_response):
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=valid_api_response)]
        mock_client.messages.create.return_value = mock_message

        result = generate_listing(sample_image, client=mock_client)

        assert isinstance(result, ListingMetadata)
        assert len(result.title) <= 140
        assert len(result.tags) <= 13
        assert all(len(tag) <= 20 for tag in result.tags)
        assert len(result.description) > 0

    def test_sends_image_to_api(self, sample_image, valid_api_response):
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=valid_api_response)]
        mock_client.messages.create.return_value = mock_message

        generate_listing(sample_image, client=mock_client, model="claude-sonnet-4-20250514")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["max_tokens"] == 2048
        assert len(call_kwargs["messages"]) == 1

        content = call_kwargs["messages"][0]["content"]
        assert content[0]["type"] == "image"
        assert content[0]["source"]["media_type"] == "image/png"
        assert content[1]["type"] == "text"

    def test_truncates_long_title(self, sample_image):
        long_title = "A" * 200
        response = json.dumps({
            "title": long_title,
            "tags": ["tag1"],
            "description": "desc",
        })
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response)]
        mock_client.messages.create.return_value = mock_message

        result = generate_listing(sample_image, client=mock_client)
        assert len(result.title) == 140

    def test_truncates_excess_tags(self, sample_image):
        response = json.dumps({
            "title": "Test",
            "tags": [f"tag{i}" for i in range(20)],
            "description": "desc",
        })
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response)]
        mock_client.messages.create.return_value = mock_message

        result = generate_listing(sample_image, client=mock_client)
        assert len(result.tags) == 13

    def test_raises_on_bad_response(self, sample_image):
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="not valid json")]
        mock_client.messages.create.return_value = mock_message

        with pytest.raises(ValueError, match="Failed to parse"):
            generate_listing(sample_image, client=mock_client)

    def test_creates_default_client_when_none(self, sample_image, valid_api_response):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=valid_api_response)]

        with patch("etsy_assistant.steps.keywords.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_message
            result = generate_listing(sample_image)
            mock_cls.assert_called_once()
            assert isinstance(result, ListingMetadata)


class TestSaveMetadata:
    @pytest.fixture
    def sample_listing(self):
        return ListingMetadata(
            title="Urban Skyline Pen Ink Print",
            tags=["pen ink", "urban art", "skyline"],
            description="A detailed pen and ink sketch of a city skyline.",
        )

    def test_saves_json_file(self, tmp_path, sample_listing):
        path = save_metadata(sample_listing, tmp_path / "listing.json")
        assert path.exists()
        assert path.suffix == ".json"
        data = json.loads(path.read_text())
        assert data["title"] == sample_listing.title
        assert data["tags"] == sample_listing.tags
        assert data["description"] == sample_listing.description

    def test_adds_json_suffix(self, tmp_path, sample_listing):
        path = save_metadata(sample_listing, tmp_path / "listing.png")
        assert path.suffix == ".json"
        assert path.exists()

    def test_creates_parent_dirs(self, tmp_path, sample_listing):
        path = save_metadata(sample_listing, tmp_path / "sub" / "dir" / "listing.json")
        assert path.exists()

    def test_roundtrip_with_load(self, tmp_path, sample_listing):
        path = save_metadata(sample_listing, tmp_path / "listing.json")
        loaded = load_metadata(path)
        assert loaded.title == sample_listing.title
        assert loaded.tags == sample_listing.tags
        assert loaded.description == sample_listing.description

    def test_preserves_unicode(self, tmp_path):
        listing = ListingMetadata(
            title="Café Street — Pen & Ink",
            tags=["café", "straße"],
            description="A charming café scene.",
        )
        path = save_metadata(listing, tmp_path / "listing.json")
        loaded = load_metadata(path)
        assert loaded.title == listing.title
        assert loaded.tags == listing.tags


class TestEncodeImageBytes:
    def test_encodes_png_bytes(self, sample_image):
        raw = sample_image.read_bytes()
        data, media_type = _encode_image_bytes(raw, ".png")
        assert media_type == "image/png"
        assert len(data) > 0

    def test_encodes_jpeg_bytes(self, sample_jpeg):
        raw = sample_jpeg.read_bytes()
        data, media_type = _encode_image_bytes(raw, ".jpg")
        assert media_type == "image/jpeg"
        assert len(data) > 0

    def test_detects_media_type_from_header(self, sample_image):
        raw = sample_image.read_bytes()
        # Even with wrong suffix, PNG header bytes should be detected
        _, media_type = _encode_image_bytes(raw, ".xyz")
        assert media_type == "image/png"


class TestGenerateListingFromBytes:
    def test_returns_listing_metadata(self, sample_image, valid_api_response):
        raw = sample_image.read_bytes()
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=valid_api_response)]
        mock_client.messages.create.return_value = mock_message

        result = generate_listing_from_bytes(raw, client=mock_client)

        assert isinstance(result, ListingMetadata)
        assert len(result.title) <= 140
        assert len(result.tags) <= 13
        assert len(result.description) > 0

    def test_sends_base64_image(self, sample_image, valid_api_response):
        raw = sample_image.read_bytes()
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=valid_api_response)]
        mock_client.messages.create.return_value = mock_message

        generate_listing_from_bytes(raw, client=mock_client)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        content = call_kwargs["messages"][0]["content"]
        assert content[0]["type"] == "image"
        assert content[0]["source"]["type"] == "base64"
        assert content[0]["source"]["media_type"] == "image/png"

    def test_raises_on_bad_response(self, sample_image):
        raw = sample_image.read_bytes()
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="not json")]
        mock_client.messages.create.return_value = mock_message

        with pytest.raises(ValueError, match="Failed to parse"):
            generate_listing_from_bytes(raw, client=mock_client)
