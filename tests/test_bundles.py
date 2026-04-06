"""Tests for the bundle listing generator."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from etsy_assistant.bundles import (
    calculate_bundle_price,
    collect_image_filenames,
    generate_bundle_description_simple,
    generate_bundle_title,
    generate_bundles,
    group_by_tags,
    load_listing_jsons,
    merge_tags,
)


@pytest.fixture
def listing_jsons(tmp_path):
    """Create a set of test listing JSONs."""
    listings = [
        {
            "title": "Vintage Trolley Pen & Ink Sketch",
            "tags": ["trolley art", "streetcar print", "pen ink sketch", "urban wall art", "digital download"],
            "description": "A vintage trolley sketch.",
        },
        {
            "title": "City Bridge Ink Drawing",
            "tags": ["bridge art", "city sketch", "pen ink sketch", "urban wall art", "digital download"],
            "description": "A city bridge drawing.",
        },
        {
            "title": "Downtown Skyline Pen Sketch",
            "tags": ["skyline art", "city print", "pen ink sketch", "urban wall art", "digital download"],
            "description": "A downtown skyline sketch.",
        },
        {
            "title": "Dahlia Flower Ink Sketch",
            "tags": ["dahlia print", "flower art", "botanical sketch", "floral decor", "digital download"],
            "description": "A dahlia flower sketch.",
        },
        {
            "title": "Rose Garden Pen Drawing",
            "tags": ["rose print", "flower art", "botanical sketch", "floral decor", "digital download"],
            "description": "A rose garden drawing.",
        },
    ]
    for i, data in enumerate(listings):
        path = tmp_path / f"listing_{i}.json"
        path.write_text(json.dumps(data))
    return tmp_path


class TestLoadListingJsons:
    def test_loads_all_jsons(self, listing_jsons):
        results = load_listing_jsons(listing_jsons)
        assert len(results) == 5

    def test_skips_bundle_jsons(self, listing_jsons):
        bundle = listing_jsons / "bundle_3pack_test.json"
        bundle.write_text(json.dumps({"title": "Bundle", "tags": []}))
        results = load_listing_jsons(listing_jsons)
        assert len(results) == 5

    def test_skips_invalid_jsons(self, listing_jsons):
        bad = listing_jsons / "bad.json"
        bad.write_text("not json")
        results = load_listing_jsons(listing_jsons)
        assert len(results) == 5


class TestGroupByTags:
    def test_groups_by_overlap(self, listing_jsons):
        listings = load_listing_jsons(listing_jsons)
        groups = group_by_tags(listings, min_overlap=3)
        assert len(groups) >= 1
        for g in groups:
            assert len(g["indices"]) >= 3
            assert "theme" in g

    def test_no_groups_if_too_few(self, tmp_path):
        (tmp_path / "a.json").write_text(json.dumps({"title": "A", "tags": ["x"]}))
        (tmp_path / "b.json").write_text(json.dumps({"title": "B", "tags": ["y"]}))
        listings = load_listing_jsons(tmp_path)
        groups = group_by_tags(listings)
        assert groups == []


class TestMergeTags:
    def test_deduplicates_and_limits(self):
        data = [
            {"tags": ["art", "print", "sketch"]},
            {"tags": ["art", "print", "drawing"]},
            {"tags": ["art", "ink", "sketch"]},
        ]
        tags = merge_tags(data, max_tags=5)
        assert len(tags) <= 5
        assert "art" in tags  # most frequent

    def test_empty_input(self):
        assert merge_tags([]) == []


class TestGenerateBundleTitle:
    def test_format(self):
        title = generate_bundle_title("Urban Sketches", 3, ["A", "B", "C"])
        assert "3-Pack" in title
        assert "Urban Sketches" in title
        assert len(title) <= 140

    def test_truncation(self):
        title = generate_bundle_title("Very Long Theme Name That Goes On And On", 5, [])
        assert len(title) <= 140


class TestCalculateBundlePrice:
    def test_3pack_discount(self):
        price = calculate_bundle_price([4.99, 4.99, 4.99], 3)
        expected = round(4.99 * 3 * 0.75, 2)
        assert price == expected

    def test_5pack_discount(self):
        price = calculate_bundle_price([4.99] * 5, 5)
        expected = round(4.99 * 5 * 0.70, 2)
        assert price == expected

    def test_mixed_prices(self):
        price = calculate_bundle_price([3.99, 5.99, 4.99], 3)
        avg = (3.99 + 5.99 + 4.99) / 3
        expected = round(avg * 3 * 0.75, 2)
        assert price == expected


class TestGenerateBundleDescriptionSimple:
    def test_contains_key_sections(self):
        data = [
            {"title": "Sketch A | Wall Art", "tags": [], "description": "Desc A"},
            {"title": "Sketch B | Wall Art", "tags": [], "description": "Desc B"},
            {"title": "Sketch C | Wall Art", "tags": [], "description": "Desc C"},
        ]
        desc = generate_bundle_description_simple("Urban Art", 3, data)
        assert "3-pack" in desc.lower()
        assert "WHAT YOU'LL RECEIVE" in desc
        assert "HOW IT WORKS" in desc
        assert "3 high-resolution" in desc


class TestGenerateBundles:
    def test_generates_bundle_files(self, listing_jsons):
        paths = generate_bundles(listing_jsons, individual_price=4.99)
        assert len(paths) >= 1
        for path in paths:
            assert path.exists()
            assert path.name.startswith("bundle_")
            data = json.loads(path.read_text())
            assert "title" in data
            assert "tags" in data
            assert "description" in data
            assert "price" in data
            assert "pack_size" in data
            assert data["pack_size"] in (3, 5)

    def test_does_not_modify_originals(self, listing_jsons):
        original_contents = {}
        for path in listing_jsons.glob("listing_*.json"):
            original_contents[path.name] = path.read_text()

        generate_bundles(listing_jsons)

        for name, content in original_contents.items():
            assert (listing_jsons / name).read_text() == content

    def test_with_manual_groups(self, listing_jsons):
        groups = [{"theme": "Test Group", "indices": [0, 1, 2]}]
        paths = generate_bundles(listing_jsons, groups=groups)
        assert len(paths) == 1  # only 3-pack (not enough for 5-pack)
        data = json.loads(paths[0].read_text())
        assert data["theme"] == "Test Group"
        assert data["pack_size"] == 3

    def test_empty_directory(self, tmp_path):
        paths = generate_bundles(tmp_path)
        assert paths == []
