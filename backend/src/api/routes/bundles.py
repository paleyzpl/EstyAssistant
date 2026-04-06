from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from etsy_assistant.bundles import (
    BUNDLE_SIZES,
    calculate_bundle_price,
    generate_bundle_description_simple,
    generate_bundle_title,
    merge_tags,
)

router = APIRouter()


class BundleListingInput(BaseModel):
    title: str
    tags: list[str]
    description: str
    price: float | None = None
    image_filenames: list[str] = Field(default_factory=list)


class GenerateBundlesRequest(BaseModel):
    listings: list[BundleListingInput]
    groups: list[dict] | None = None
    default_price: float = 4.99


class BundleOutput(BaseModel):
    theme: str
    pack_size: int
    title: str
    tags: list[str]
    description: str
    price: float
    image_filenames: list[str]
    source_indices: list[int]


class GenerateBundlesResponse(BaseModel):
    bundles: list[BundleOutput]


@router.post("/bundles/generate", response_model=GenerateBundlesResponse)
def generate_bundles(req: GenerateBundlesRequest):
    """Generate bundle listings from individual listing metadata.

    If groups are not provided, groups listings by tag overlap.
    """
    if len(req.listings) < 3:
        raise HTTPException(status_code=400, detail="Need at least 3 listings to create bundles")

    # Determine groups
    if req.groups:
        resolved_groups = req.groups
    else:
        # Simple tag-overlap grouping
        from etsy_assistant.bundles import group_by_tags
        fake_listings = [(None, {"title": l.title, "tags": l.tags}) for l in req.listings]
        resolved_groups = group_by_tags(fake_listings, min_overlap=2)

    if not resolved_groups:
        raise HTTPException(status_code=400, detail="Could not form any groups from the provided listings")

    bundles = []
    for group in resolved_groups:
        theme = group["theme"]
        indices = group["indices"]

        for pack_size in BUNDLE_SIZES:
            if len(indices) < pack_size:
                continue

            selected = indices[:pack_size]
            selected_data = [
                {"title": req.listings[i].title, "tags": req.listings[i].tags,
                 "description": req.listings[i].description}
                for i in selected
            ]

            title = generate_bundle_title(theme, pack_size, [d["title"] for d in selected_data])
            tags = merge_tags(selected_data)

            bundle_tag = f"{pack_size} pack prints"
            if bundle_tag not in tags and len(tags) < 13:
                tags.insert(0, bundle_tag)
            if "art bundle" not in tags and len(tags) < 13:
                tags.insert(1, "art bundle")

            prices = [
                req.listings[i].price or req.default_price
                for i in selected
            ]
            price = calculate_bundle_price(prices, pack_size)

            description = generate_bundle_description_simple(theme, pack_size, selected_data)

            image_filenames = []
            for i in selected:
                image_filenames.extend(req.listings[i].image_filenames)

            bundles.append(BundleOutput(
                theme=theme,
                pack_size=pack_size,
                title=title,
                tags=tags,
                description=description,
                price=price,
                image_filenames=image_filenames,
                source_indices=selected,
            ))

    return GenerateBundlesResponse(bundles=bundles)
