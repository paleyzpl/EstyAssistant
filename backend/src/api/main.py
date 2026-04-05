import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from api.models import HealthResponse
from api.routes import listing, mockups, process, upload

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s: %(message)s",
)

app = FastAPI(
    title="Etsy Assistant API",
    version="0.1.0",
    description="Image processing and listing generation for Carrot Sketches",
)

# CORS: allow the Vercel frontend
ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, tags=["upload"])
app.include_router(process.router, tags=["process"])
app.include_router(listing.router, tags=["listing"])
app.include_router(mockups.router, tags=["mockups"])


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


# Lambda handler via Mangum
handler = Mangum(app, lifespan="off")
