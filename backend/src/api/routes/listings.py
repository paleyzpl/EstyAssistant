import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.credentials import delete_listing, get_listing, list_listings, save_listing

router = APIRouter()


class SaveListingRequest(BaseModel):
    title: str
    tags: list[str]
    description: str
    price: float | None = None
    s3_key: str | None = None
    sizes: list[str] = Field(default_factory=list)
    etsy_listing_id: str | None = None
    etsy_listing_url: str | None = None
    preview_url: str | None = None


class ListingItem(BaseModel):
    id: str
    title: str
    tags: list[str]
    description: str
    price: float | None = None
    s3_key: str | None = None
    sizes: list[str] = Field(default_factory=list)
    etsy_listing_id: str | None = None
    etsy_listing_url: str | None = None
    preview_url: str | None = None
    created_at: int = 0


class ListListingsResponse(BaseModel):
    listings: list[ListingItem]


@router.get("/listings", response_model=ListListingsResponse)
def get_all_listings(limit: int = 50):
    """List saved listings, most recent first."""
    items = list_listings(limit=limit)
    return ListListingsResponse(listings=[ListingItem(**item) for item in items])


@router.get("/listings/{listing_id}", response_model=ListingItem)
def get_single_listing(listing_id: str):
    """Get a single listing by ID."""
    item = get_listing(listing_id)
    if not item:
        raise HTTPException(status_code=404, detail="Listing not found")
    return ListingItem(**item)


@router.post("/listings", response_model=ListingItem)
def save_new_listing(req: SaveListingRequest):
    """Save a listing to history."""
    listing_id = uuid.uuid4().hex[:12]
    item = save_listing(
        listing_id=listing_id,
        title=req.title,
        tags=req.tags,
        description=req.description,
        price=req.price,
        s3_key=req.s3_key,
        sizes=req.sizes,
        etsy_listing_id=req.etsy_listing_id,
        etsy_listing_url=req.etsy_listing_url,
        preview_url=req.preview_url,
    )
    return ListingItem(**item)


@router.delete("/listings/{listing_id}")
def remove_listing(listing_id: str):
    """Delete a listing from history."""
    deleted = delete_listing(listing_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"success": True}
