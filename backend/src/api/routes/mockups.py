import uuid

from fastapi import APIRouter, HTTPException

from api.models import MockupGenerateRequest, MockupGenerateResponse, MockupImage
from api.s3 import read_image, write_image
from etsy_assistant.steps.mockup import generate_all_mockups_bytes, generate_mockup_bytes

router = APIRouter()


@router.post("/mockups/generate", response_model=MockupGenerateResponse)
def generate_mockups(req: MockupGenerateRequest):
    """Generate frame mockup images for a processed sketch."""
    try:
        image_bytes = read_image(req.s3_key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image not found: {req.s3_key}") from e

    batch_id = uuid.uuid4().hex[:12]

    try:
        if req.template_names:
            results = []
            for name in req.template_names:
                tname, data = generate_mockup_bytes(image_bytes, name)
                results.append((tname, data))
        else:
            results = generate_all_mockups_bytes(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mockup generation failed: {e}") from e

    mockups = []
    for template_name, jpeg_data in results:
        s3_key = f"mockups/{batch_id}/{template_name}.jpg"
        url = write_image(s3_key, jpeg_data, content_type="image/jpeg")
        mockups.append(MockupImage(template_name=template_name, url=url))

    return MockupGenerateResponse(mockups=mockups)
