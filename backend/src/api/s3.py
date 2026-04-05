import logging
import os
import uuid

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("S3_BUCKET", "etsy-assistant-images")
REGION = os.environ.get("AWS_REGION", "us-east-1")
PRESIGN_EXPIRY = 3600  # 1 hour

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            region_name=REGION,
            config=Config(signature_version="s3v4"),
        )
    return _client


def generate_upload_url(content_type: str = "image/jpeg") -> tuple[str, str]:
    """Generate a presigned URL for direct browser upload to S3.

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
    """Read an image from S3."""
    s3 = _get_client()
    resp = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    data = resp["Body"].read()
    logger.info("Read %d bytes from s3://%s/%s", len(data), BUCKET_NAME, s3_key)
    return data


def write_image(s3_key: str, data: bytes, content_type: str = "image/png") -> str:
    """Write an image to S3 and return a presigned download URL."""
    s3 = _get_client()
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=data,
        ContentType=content_type,
    )
    logger.info("Wrote %d bytes to s3://%s/%s", len(data), BUCKET_NAME, s3_key)

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": s3_key},
        ExpiresIn=PRESIGN_EXPIRY,
    )
    return url
