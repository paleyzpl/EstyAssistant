"""Bundle listing generator for Etsy.

Reads individual listing JSONs and generates 3-pack and 5-pack bundle
listings with merged metadata and discounted pricing.
"""

import csv
import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from etsy_assistant.steps.keywords import ListingMetadata

logger = logging.getLogger(__name__)

BUNDLE_SIZES = {
    3: {"label": "3-Pack", "discount": 0.75},
    5: {"label": "5-Pack", "discount": 0.70},
}

GROUPING_SYSTEM_PROMPT = """\
You are a merchandising expert for an Etsy shop called "Carrot Sketches" \
that sells pen & ink sketch printable wall art.

Given a list of individual listing titles and tags, group them into \
coherent bundles that would make sense to buy together. Each group \
should share a visual style, theme, or subject matter.

RULES:
- Each listing can appear in multiple groups (but each group must be unique)
- A group needs at least 3 items for a 3-pack, 5 for a 5-pack
- Name each group with a short theme label (2-4 words)
- Prefer groupings that tell a story or create a cohesive gallery wall

Respond with ONLY valid JSON matching this schema:
{
  "groups": [
    {
      "theme": "string (2-4 word theme label)",
      "indices": [0, 1, 2]
    }
  ]
}

The indices refer to the position in the input list (0-indexed).
"""

BUNDLE_DESCRIPTION_PROMPT = """\
You are an Etsy SEO expert for "Carrot Sketches" printable wall art shop.

Given individual listing descriptions for a {pack_size}-pack bundle \
themed "{theme}", write a cohesive bundle description.

FORMAT:
- Start with a 1-2 sentence hook about the bundle value
- Mention the theme and what ties them together
- List what's included (number of prints, sizes, DPI)
- Include the same sections as individual listings: \
WHAT YOU'LL RECEIVE, HOW IT WORKS, PRINTING TIPS, STYLING IDEAS, PLEASE NOTE
- Emphasize the bundle discount and gallery wall potential
- Use ✦ for headers, • for bullets
- Do NOT use markdown

Respond with ONLY the description text (no JSON wrapping).
"""


@dataclass
class BundleListing:
    theme: str
    pack_size: int
    title: str
    tags: list[str]
    description: str
    price: float
    image_filenames: list[str]
    source_listings: list[str] = field(default_factory=list)


def load_listing_jsons(directory: Path) -> list[tuple[Path, dict]]:
    """Load all listing JSON files from a directory.

    Returns list of (path, data) tuples sorted by filename.
    Skips bundle JSONs (files starting with 'bundle_').
    """
    directory = Path(directory)
    results = []
    for path in sorted(directory.glob("*.json")):
        if path.stem.startswith("bundle_"):
            continue
        try:
            data = json.loads(path.read_text())
            if "title" in data and "tags" in data:
                results.append((path, data))
        except (json.JSONDecodeError, KeyError):
            logger.warning("Skipping invalid JSON: %s", path)
    return results


def load_etsy_csv(csv_path: Path) -> list[dict]:
    """Load an Etsy listing export CSV for grouping hints.

    Returns list of dicts with keys: title, tags, price, url.
    """
    csv_path = Path(csv_path)
    results = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Etsy exports use UPPER CASE column names
            lrow = {k.lower(): v for k, v in row.items()}
            results.append({
                "title": lrow.get("title", ""),
                "tags": lrow.get("tags", ""),
                "price": lrow.get("price", ""),
                "url": lrow.get("url", ""),
            })
    return results


def group_by_tags(listings: list[tuple[Path, dict]],
                  min_overlap: int = 3) -> list[dict]:
    """Group listings by tag overlap (non-AI fallback).

    Returns list of {"theme": str, "indices": list[int]}.
    """
    n = len(listings)
    if n < 3:
        return []

    # Build tag sets
    tag_sets = []
    for _, data in listings:
        tag_sets.append(set(t.lower() for t in data.get("tags", [])))

    # Find groups with sufficient tag overlap
    groups = []
    used_combos = set()

    for i in range(n):
        group_indices = [i]
        for j in range(n):
            if i == j:
                continue
            overlap = len(tag_sets[i] & tag_sets[j])
            if overlap >= min_overlap:
                group_indices.append(j)

        if len(group_indices) >= 3:
            key = tuple(sorted(group_indices[:5]))
            if key not in used_combos:
                used_combos.add(key)
                # Derive theme from most common shared tags
                shared_tags = tag_sets[group_indices[0]]
                for idx in group_indices[1:]:
                    shared_tags = shared_tags & tag_sets[idx]
                theme = " ".join(list(shared_tags)[:3]).title() if shared_tags else "Mixed Collection"
                groups.append({
                    "theme": theme,
                    "indices": group_indices[:5],
                })

    return groups


def group_with_ai(listings: list[tuple[Path, dict]],
                  client: anthropic.Anthropic | None = None,
                  csv_data: list[dict] | None = None) -> list[dict]:
    """Use Claude to intelligently group listings into bundles.

    Returns list of {"theme": str, "indices": list[int]}.
    """
    client = client or anthropic.Anthropic()

    listing_descriptions = []
    for i, (path, data) in enumerate(listings):
        tags_str = ", ".join(data.get("tags", []))
        listing_descriptions.append(
            f"{i}. \"{data['title']}\" — tags: [{tags_str}]"
        )

    prompt = "Here are the individual listings:\n\n" + "\n".join(listing_descriptions)

    if csv_data:
        csv_titles = [d["title"] for d in csv_data if d.get("title")][:20]
        prompt += "\n\nExisting Etsy shop listings for reference:\n"
        prompt += "\n".join(f"- {t}" for t in csv_titles)

    prompt += f"\n\nThere are {len(listings)} listings. Generate groupings for 3-packs and 5-packs."

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=GROUPING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines)

    data = json.loads(response_text)
    return data.get("groups", [])


def group_from_config(config_path: Path) -> list[dict]:
    """Load manual grouping from a config JSON file.

    Expected format:
    {
      "groups": [
        {"theme": "Urban Sketches", "files": ["tram.json", "city.json", "bridge.json"]}
      ]
    }
    """
    data = json.loads(Path(config_path).read_text())
    return data.get("groups", [])


def merge_tags(listings_data: list[dict], max_tags: int = 13) -> list[str]:
    """Merge and deduplicate tags from multiple listings, prioritizing frequent ones."""
    counter: Counter[str] = Counter()
    for data in listings_data:
        for tag in data.get("tags", []):
            counter[tag.lower().strip()] += 1

    # Sort by frequency (most common first), then alphabetically
    sorted_tags = sorted(counter.keys(), key=lambda t: (-counter[t], t))

    # Add bundle-specific tags at the beginning
    bundle_tags = []
    for tag in sorted_tags:
        if len(bundle_tags) >= max_tags:
            break
        if tag not in bundle_tags:
            bundle_tags.append(tag)

    return bundle_tags[:max_tags]


def generate_bundle_title(theme: str, pack_size: int,
                          source_titles: list[str]) -> str:
    """Generate a bundle title from theme and pack size."""
    label = BUNDLE_SIZES[pack_size]["label"]
    title = f"{label} {theme} Ink Sketch Prints | Black and White Wall Art Bundle | Printable Drawing Set"
    return title[:140]


def calculate_bundle_price(individual_prices: list[float],
                           pack_size: int) -> float:
    """Calculate discounted bundle price."""
    avg_price = sum(individual_prices) / len(individual_prices) if individual_prices else 4.99
    discount = BUNDLE_SIZES[pack_size]["discount"]
    return round(avg_price * pack_size * discount, 2)


def generate_bundle_description(
    theme: str,
    pack_size: int,
    listings_data: list[dict],
    client: anthropic.Anthropic | None = None,
) -> str:
    """Generate a bundle description using Claude."""
    client = client or anthropic.Anthropic()

    individual_descriptions = "\n\n---\n\n".join(
        f"Listing {i+1}: {d['title']}\n{d.get('description', '')}"
        for i, d in enumerate(listings_data)
    )

    prompt = BUNDLE_DESCRIPTION_PROMPT.format(
        pack_size=pack_size, theme=theme
    ) + f"\n\nIndividual listings:\n\n{individual_descriptions}"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()


def generate_bundle_description_simple(
    theme: str,
    pack_size: int,
    listings_data: list[dict],
) -> str:
    """Generate a bundle description without AI (template-based fallback)."""
    titles = [d["title"].split("|")[0].strip() for d in listings_data]
    titles_list = "\n".join(f"• {t}" for t in titles)
    label = BUNDLE_SIZES[pack_size]["label"]
    discount_pct = int((1 - BUNDLE_SIZES[pack_size]["discount"]) * 100)

    return f"""\
Save {discount_pct}% with this curated {label.lower()} of {theme.lower()} pen & ink sketch prints! \
This collection brings together beautifully hand-drawn artwork perfect for creating a cohesive gallery wall.

✦ WHAT'S INCLUDED ✦
{titles_list}

✦ WHAT YOU'LL RECEIVE ✦
• {pack_size} high-resolution digital files (300 DPI)
• Each print suitable for printing up to 16x20 inches
• Instant download - no waiting for shipping!

✦ HOW IT WORKS ✦
1. Complete your purchase
2. Go to your Etsy account > Purchases & Reviews
3. Click "Download Files" next to this order
4. Print at home or at a local print shop
5. Frame and enjoy!

✦ PRINTING TIPS ✦
• Print on bright white or cream cardstock for best contrast
• Use high-quality inkjet or laser printer settings
• Black and white ink drawings look stunning on textured paper
• All prints in this set coordinate beautifully together

✦ STYLING IDEAS ✦
Display all {pack_size} prints together as a gallery wall for maximum impact. \
The cohesive {theme.lower()} theme creates a curated look that's perfect for \
living rooms, bedrooms, offices, or hallways. Mix frame styles for an eclectic vibe \
or use matching frames for a clean, modern aesthetic. \
Makes a thoughtful gift for art lovers and home decor enthusiasts.

✦ PLEASE NOTE ✦
• This is a DIGITAL DOWNLOAD - no physical items will be mailed
• Colors may vary slightly depending on your monitor and printer
• For personal use only

© Carrot Sketches - Personal use only."""


def collect_image_filenames(source_paths: list[Path]) -> list[str]:
    """Collect mockup and processed image filenames for the bundle."""
    filenames = []
    for path in source_paths:
        stem = path.stem.replace("_clean", "").replace(".json", "")
        parent = path.parent
        # Look for processed images and mockups
        for pattern in [f"{stem}_clean_*.png", f"{stem}_mockup_*.jpg", f"{stem}_clean.png"]:
            for img_path in parent.glob(pattern):
                filenames.append(img_path.name)
    return filenames


def generate_bundles(
    directory: Path,
    groups: list[dict] | None = None,
    config_path: Path | None = None,
    csv_path: Path | None = None,
    use_ai_grouping: bool = False,
    use_ai_description: bool = False,
    individual_price: float = 4.99,
    client: anthropic.Anthropic | None = None,
) -> list[Path]:
    """Generate bundle listing JSONs from individual listings.

    Args:
        directory: Directory containing individual listing JSONs.
        groups: Pre-computed groups (overrides all grouping logic).
        config_path: Manual grouping config file.
        csv_path: Optional Etsy CSV export for grouping hints.
        use_ai_grouping: Use Claude for intelligent grouping.
        use_ai_description: Use Claude for bundle descriptions.
        individual_price: Default price per item if not specified.
        client: Optional Anthropic client.

    Returns:
        List of paths to generated bundle JSON files.
    """
    directory = Path(directory)
    listings = load_listing_jsons(directory)

    if not listings:
        logger.warning("No listing JSONs found in %s", directory)
        return []

    logger.info("Found %d listing JSONs in %s", len(listings), directory)

    # Determine groups
    if groups:
        resolved_groups = groups
    elif config_path:
        config_groups = group_from_config(config_path)
        # Convert file-based groups to index-based
        filename_to_idx = {p.name: i for i, (p, _) in enumerate(listings)}
        resolved_groups = []
        for g in config_groups:
            indices = [filename_to_idx[f] for f in g["files"] if f in filename_to_idx]
            if len(indices) >= 3:
                resolved_groups.append({"theme": g["theme"], "indices": indices})
    elif use_ai_grouping:
        csv_data = load_etsy_csv(csv_path) if csv_path else None
        resolved_groups = group_with_ai(listings, client, csv_data)
    else:
        resolved_groups = group_by_tags(listings)

    if not resolved_groups:
        logger.warning("No valid groups found. Falling back to tag-based grouping.")
        resolved_groups = group_by_tags(listings, min_overlap=2)

    if not resolved_groups:
        logger.error("Could not form any groups from %d listings", len(listings))
        return []

    logger.info("Found %d groups", len(resolved_groups))

    # Generate bundles for each group
    output_paths = []
    for group in resolved_groups:
        theme = group["theme"]
        indices = group["indices"]

        for pack_size, config in BUNDLE_SIZES.items():
            if len(indices) < pack_size:
                continue

            selected_indices = indices[:pack_size]
            selected_paths = [listings[i][0] for i in selected_indices]
            selected_data = [listings[i][1] for i in selected_indices]

            # Build bundle metadata
            title = generate_bundle_title(theme, pack_size, [d["title"] for d in selected_data])
            tags = merge_tags(selected_data)

            # Add bundle-specific tags
            bundle_tag = f"{pack_size} pack prints"
            if bundle_tag not in tags and len(tags) < 13:
                tags.insert(0, bundle_tag)
            if "art bundle" not in tags and len(tags) < 13:
                tags.insert(1, "art bundle")

            # Price
            prices = []
            for d in selected_data:
                if "price" in d:
                    prices.append(float(d["price"]))
                else:
                    prices.append(individual_price)
            price = calculate_bundle_price(prices, pack_size)

            # Description
            if use_ai_description:
                description = generate_bundle_description(theme, pack_size, selected_data, client)
            else:
                description = generate_bundle_description_simple(theme, pack_size, selected_data)

            # Image filenames
            image_filenames = collect_image_filenames(selected_paths)

            # Save bundle JSON
            safe_theme = theme.lower().replace(" ", "_").replace("/", "_")
            filename = f"bundle_{pack_size}pack_{safe_theme}.json"
            output_path = directory / filename

            bundle_data = {
                "title": title,
                "tags": tags,
                "description": description,
                "price": price,
                "image_filenames": image_filenames,
                "source_listings": [p.name for p in selected_paths],
                "pack_size": pack_size,
                "theme": theme,
            }

            output_path.write_text(json.dumps(bundle_data, indent=2, ensure_ascii=False) + "\n")
            logger.info("Generated %s: %s ($%.2f)", filename, title[:50], price)
            output_paths.append(output_path)

    return output_paths
