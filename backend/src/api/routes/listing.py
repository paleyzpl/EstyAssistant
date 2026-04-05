from fastapi import APIRouter, HTTPException

from api.models import ListingGenerateRequest, ListingMetadataResponse
from api.s3 import read_image
from etsy_assistant.steps.keywords import generate_listing_from_bytes

router = APIRouter()


@router.post("/listing/generate", response_model=ListingMetadataResponse)
def generate_listing(req: ListingGenerateRequest):
    """Generate AI-powered Etsy listing metadata for a processed image."""
    try:
        image_bytes = read_image(req.s3_key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image not found: {req.s3_key}") from e

    try:
        listing = generate_listing_from_bytes(image_bytes, model=req.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Listing generation failed: {e}") from e

    return ListingMetadataResponse(
        title=listing.title,
        tags=listing.tags,
        description=listing.description,
    )
