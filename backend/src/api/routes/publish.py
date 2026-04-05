import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.credentials import (
    create_job,
    get_job,
    load_credentials,
    save_credentials,
    update_job,
)
from api.s3 import read_image
from etsy_assistant.etsy_api import (
    EtsyCredentials,
    create_draft_listing,
    upload_listing_file_bytes,
    upload_listing_image_bytes,
)
from etsy_assistant.pipeline import process_image_bytes

logger = logging.getLogger(__name__)

router = APIRouter()


class PublishRequest(BaseModel):
    s3_key: str
    sizes: list[str] = Field(default_factory=lambda: ["8x10"])
    title: str
    description: str
    tags: list[str]
    price: float


class PublishResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    result: dict | None = None
    error: str | None = None


def _on_token_refresh(creds: EtsyCredentials) -> None:
    """Callback to save refreshed tokens to DynamoDB."""
    save_credentials(
        api_key=creds.api_key,
        access_token=creds.access_token,
        refresh_token=creds.refresh_token,
        user_id=creds.user_id,
        shop_id=creds.shop_id,
    )


@router.post("/publish", response_model=PublishResponse)
def publish_listing(req: PublishRequest):
    """Process image, create Etsy draft listing, upload files.

    Runs synchronously (Lambda has up to 60s timeout).
    For truly long operations, consider async invocation.
    """
    creds_data = load_credentials()
    if not creds_data:
        raise HTTPException(status_code=401, detail="Etsy not connected. Go to Settings to connect.")

    creds = EtsyCredentials(**creds_data)

    job_id = uuid.uuid4().hex[:12]
    create_job(job_id)

    try:
        update_job(job_id, "processing")

        # Read and process image
        image_bytes = read_image(req.s3_key)
        results = process_image_bytes(image_bytes, sizes=req.sizes)

        # Create draft listing
        draft = create_draft_listing(
            creds, req.title, req.description, req.tags, req.price,
        )

        # Upload first processed image as preview
        if results:
            first_label, first_bytes = results[0]
            upload_listing_image_bytes(
                creds, draft.listing_id, first_bytes,
                filename=f"{first_label}.png",
                on_refresh=_on_token_refresh,
            )

        # Upload all sizes as digital download files
        for size_label, png_data in results:
            upload_listing_file_bytes(
                creds, draft.listing_id, png_data,
                filename=f"{size_label}.png",
                on_refresh=_on_token_refresh,
            )

        update_job(job_id, "completed", result={
            "listing_id": draft.listing_id,
            "listing_url": draft.url,
            "title": draft.title,
        })

    except Exception as e:
        logger.exception("Publish failed for job %s", job_id)
        update_job(job_id, "failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Publish failed: {e}") from e

    return PublishResponse(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """Poll job status."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job)
