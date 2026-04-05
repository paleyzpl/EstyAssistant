from fastapi import APIRouter, Query

from api.models import UploadUrlResponse
from api.s3 import generate_upload_url

router = APIRouter()


@router.get("/upload-url", response_model=UploadUrlResponse)
def get_upload_url(
    content_type: str = Query(default="image/jpeg"),
):
    """Generate a presigned S3 URL for direct browser upload."""
    url, s3_key = generate_upload_url(content_type)
    return UploadUrlResponse(upload_url=url, s3_key=s3_key)
