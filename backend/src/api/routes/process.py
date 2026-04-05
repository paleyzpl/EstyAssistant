import uuid

from fastapi import APIRouter, HTTPException

from api.models import ProcessedImage, ProcessRequest, ProcessResponse
from api.s3 import read_image, write_image
from etsy_assistant.pipeline import process_image_bytes

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
def process_sketch(req: ProcessRequest):
    """Run the CV pipeline on an uploaded image.

    Reads the original from S3, processes it, writes outputs back to S3,
    and returns presigned download URLs.
    """
    try:
        image_bytes = read_image(req.s3_key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image not found: {req.s3_key}") from e

    skip = set(req.skip_steps)
    try:
        results = process_image_bytes(image_bytes, sizes=req.sizes, skip_steps=skip)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}") from e

    batch_id = uuid.uuid4().hex[:12]
    outputs = []
    preview_url = ""

    for size_label, png_data in results:
        s3_key = f"processed/{batch_id}/{size_label}.png"
        url = write_image(s3_key, png_data)
        outputs.append(ProcessedImage(size=size_label, download_url=url))
        if not preview_url:
            preview_url = url

    return ProcessResponse(preview_url=preview_url, outputs=outputs)
