import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an Etsy SEO expert for printable wall art. The shop is called \
"Carrot Sketches" and sells hand-drawn pen & ink sketch prints as digital \
downloads for home decor.

Given an image of a pen & ink sketch, generate optimized Etsy listing metadata.

TITLE FORMAT:
Follow this pattern from a best-selling listing:
"Jefferson Memorial Ink Sketch | Black and White Architecture Wall Art | Washington DC Printable Drawing"
- Format: [Subject] Ink Sketch | Black and White [Category] Wall Art | [Location/Theme] Printable Drawing
- Max 140 chars, pipe-separated, keyword-rich

DESCRIPTION FORMAT:
Write 300-400 words in this exact structure. Use Unicode symbols for section \
headers. Write in a warm, concise tone. Include natural SEO keywords throughout.

Structure to follow:

[1-2 sentence emotional hook describing the artwork. Front-load primary keywords. \
This must be compelling within 160 characters as only this shows before "Read more".]

✦ WHAT YOU'LL RECEIVE ✦
• 1 high-resolution digital file (300 DPI JPG)
• Suitable for printing up to 16x20 inches
• Instant download - no waiting for shipping!

✦ HOW IT WORKS ✦
1. Complete your purchase
2. Go to your Etsy account > Purchases & Reviews
3. Click "Download Files" next to this order
4. Print at home or at a local print shop
5. Frame and enjoy!

✦ PRINTING TIPS ✦
[2-3 bullet points about paper type, print settings, and where to print. \
Mention that black and white ink drawings look stunning on bright white or cream paper.]

✦ STYLING IDEAS ✦
[2-3 sentences about which rooms and decor styles it suits. Mention gallery wall, \
solo statement piece. Reference specific aesthetics: modern, farmhouse, minimalist, etc. \
Include gift suggestions.]

✦ PLEASE NOTE ✦
• This is a DIGITAL DOWNLOAD - no physical item will be mailed
• Colors may vary slightly depending on your monitor and printer
• For personal use only

© Carrot Sketches - Personal use only.

IMPORTANT RULES:
- Keep the same warm, concise tone as the shop's existing listings
- Include keyword variations naturally (ink sketch, pen drawing, hand-drawn, etc.)
- The first sentence must work as a standalone hook
- Use ✦ for section headers, • for bullets, numbered lists for steps
- Do NOT use markdown formatting

Respond with ONLY valid JSON matching this schema:
{
  "title": "string (max 140 chars)",
  "tags": ["string (max 13 tags, each max 20 chars, relevant Etsy search terms)"],
  "description": "string (follow the structure above exactly, use \\n for newlines)"
}
"""


@dataclass(frozen=True)
class ListingMetadata:
    title: str
    tags: list[str]
    description: str


def _detect_media_type(raw: bytes, suffix: str) -> str:
    """Detect image media type from file header bytes, falling back to extension."""
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:2] == b"\xff\xd8":
        return "image/jpeg"
    if raw[:4] == b"GIF8":
        return "image/gif"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    ext_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    return ext_types.get(suffix.lower(), "image/png")


def _encode_image(image_path: Path) -> tuple[str, str]:
    """Read and base64-encode an image file. Returns (data, media_type)."""
    raw = image_path.read_bytes()
    media_type = _detect_media_type(raw, image_path.suffix)
    data = base64.standard_b64encode(raw).decode("utf-8")
    return data, media_type


def _encode_image_bytes(raw: bytes, suffix: str = ".png") -> tuple[str, str]:
    """Base64-encode image bytes. Returns (data, media_type)."""
    media_type = _detect_media_type(raw, suffix)
    data = base64.standard_b64encode(raw).decode("utf-8")
    return data, media_type


def _parse_response(text: str) -> dict:
    """Extract JSON from the model response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code fences
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def generate_listing(
    image_path: Path,
    *,
    client: anthropic.Anthropic | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> ListingMetadata:
    """Send a sketch image to Claude Vision and get Etsy listing metadata.

    Args:
        image_path: Path to the processed sketch image.
        client: Optional pre-configured Anthropic client.
        model: Claude model to use.

    Returns:
        ListingMetadata with title, tags, and description.

    Raises:
        anthropic.APIError: On API failures.
        ValueError: If the response cannot be parsed.
    """
    client = client or anthropic.Anthropic()
    image_path = Path(image_path)

    image_data, media_type = _encode_image(image_path)

    logger.info("Sending image to Claude for listing generation: %s", image_path.name)

    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Generate an optimized Etsy listing for this pen & ink sketch print.",
                    },
                ],
            }
        ],
        system=SYSTEM_PROMPT,
    )

    response_text = message.content[0].text
    logger.debug("Raw API response: %s", response_text)

    try:
        data = _parse_response(response_text)
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse listing metadata from API response: {e}") from e

    # Validate and enforce constraints
    title = data["title"][:140]
    tags = [tag[:20] for tag in data["tags"][:13]]
    description = data["description"]

    result = ListingMetadata(title=title, tags=tags, description=description)
    logger.info("Generated listing: %s (%d tags)", title, len(tags))
    return result


def save_metadata(listing: ListingMetadata, output_path: Path) -> Path:
    """Save listing metadata as a JSON sidecar file.

    Args:
        listing: The listing metadata to save.
        output_path: Path for the JSON file (.json extension added if missing).

    Returns:
        Path to the saved JSON file.
    """
    output_path = Path(output_path)
    if output_path.suffix != ".json":
        output_path = output_path.with_suffix(".json")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "title": listing.title,
        "tags": listing.tags,
        "description": listing.description,
    }
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    logger.info("Saved listing metadata: %s", output_path)
    return output_path


def load_metadata(json_path: Path) -> ListingMetadata:
    """Load listing metadata from a JSON sidecar file."""
    data = json.loads(Path(json_path).read_text())
    return ListingMetadata(
        title=data["title"],
        tags=data["tags"],
        description=data["description"],
    )


def generate_listing_from_bytes(
    image_bytes: bytes,
    *,
    suffix: str = ".png",
    client: anthropic.Anthropic | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> ListingMetadata:
    """Generate Etsy listing metadata from in-memory image bytes.

    Same as generate_listing() but accepts bytes instead of a file path.
    """
    client = client or anthropic.Anthropic()
    image_data, media_type = _encode_image_bytes(image_bytes, suffix)

    logger.info("Sending image bytes to Claude for listing generation")

    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Generate an optimized Etsy listing for this pen & ink sketch print.",
                    },
                ],
            }
        ],
        system=SYSTEM_PROMPT,
    )

    response_text = message.content[0].text
    logger.debug("Raw API response: %s", response_text)

    try:
        data = _parse_response(response_text)
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse listing metadata from API response: {e}") from e

    title = data["title"][:140]
    tags = [tag[:20] for tag in data["tags"][:13]]
    description = data["description"]

    result = ListingMetadata(title=title, tags=tags, description=description)
    logger.info("Generated listing: %s (%d tags)", title, len(tags))
    return result
