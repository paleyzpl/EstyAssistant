from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str


class ProcessRequest(BaseModel):
    s3_key: str
    sizes: list[str] = Field(default_factory=lambda: ["8x10"])
    skip_steps: list[str] = Field(default_factory=list)


class ProcessedImage(BaseModel):
    size: str
    download_url: str


class ProcessResponse(BaseModel):
    preview_url: str
    outputs: list[ProcessedImage]


class ListingGenerateRequest(BaseModel):
    s3_key: str
    model: str = "claude-sonnet-4-20250514"


class ListingMetadataResponse(BaseModel):
    title: str
    tags: list[str]
    description: str
