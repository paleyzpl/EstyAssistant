"""S3-compatible object storage (works with AWS S3 or Supabase Storage).

Controlled via STORAGE_BACKEND env var:
- "s3" (default): AWS S3
- "supabase": Supabase Storage (S3-compatible endpoint)

Supabase config requires:
- SUPABASE_URL (e.g., https://abc.supabase.co)
- SUPABASE_S3_ACCESS_KEY_ID
- SUPABASE_S3_SECRET_ACCESS_KEY
- S3_BUCKET (the bucket name)
"""

import logging
import os
import uuid

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

BACKEND = os.environ.get("STORAGE_BACKEND", "s3")
BUCKET_NAME = os.environ.get("S3_BUCKET", "etsy-assistant-images")
REGION = os.environ.get("AWS_REGION", "us-east-1")
PRESIGN_EXPIRY = 3600  # 1 hour

# Supabase config (only used if BACKEND == "supabase")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    if BACKEND == "supabase":
        # Supabase Storage S3-compatible endpoint
        # Format: https://<project-ref>.supabase.co/storage/v1/s3
        if not SUPABASE_URL:
            raise ValueError("SUPABASE_URL is required for Supabase storage backend")
        endpoint_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/s3"
        _client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=REGION,
            aws_access_key_id=os.environ.get("SUPABASE_S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("SUPABASE_S3_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
        )
        logger.info("Using Supabase Storage backend: %s", endpoint_url)
    else:
        _client = boto3.client(
            "s3",
            region_name=REGION,
            config=Config(signature_version="s3v4"),
        )
        logger.info("Using AWS S3 backend")

    return _client


def generate_upload_url(content_type: str = "image/jpeg") -> tuple[str, str]:
    """Generate a presigned URL for direct browser upload.

    Returns (presigned_url, s3_key).
    """
    s3 = _get_client()
    s3_key = f"uploads/{uuid.uuid4().hex}"

    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": s3_key,
            "ContentType": content_type,
        },
        ExpiresIn=PRESIGN_EXPIRY,
    )
    logger.info("Generated upload URL for key: %s", s3_key)
    return url, s3_key


def read_image(s3_key: str) -> bytes:
    """Read an image from object storage."""
    s3 = _get_client()
    resp = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    data = resp["Body"].read()
    logger.info("Read %d bytes from %s/%s", len(data), BUCKET_NAME, s3_key)
    return data


def write_image(s3_key: str, data: bytes, content_type: str = "image/png") -> str:
    """Write an image to storage and return a presigned download URL."""
    s3 = _get_client()
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=data,
        ContentType=content_type,
    )
    logger.info("Wrote %d bytes to %s/%s", len(data), BUCKET_NAME, s3_key)

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": s3_key},
        ExpiresIn=PRESIGN_EXPIRY,
    )
    return url
