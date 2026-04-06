import logging
import os
import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from api.models import HealthResponse
from api.routes import analytics, auth, bundles, listing, listings, mockups, process, publish, templates, upload

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

# Simple in-memory rate limiter (per-IP, resets on cold start)
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
_request_counts: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0

    # Clean old entries
    _request_counts[client_ip] = [t for t in _request_counts[client_ip] if now - t < window]

    if len(_request_counts[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again in a minute."},
        )

    _request_counts[client_ip].append(now)
    return await call_next(request)


app.include_router(upload.router, tags=["upload"])
app.include_router(process.router, tags=["process"])
app.include_router(listing.router, tags=["listing"])
app.include_router(mockups.router, tags=["mockups"])
app.include_router(auth.router, tags=["auth"])
app.include_router(publish.router, tags=["publish"])
app.include_router(listings.router, tags=["listings"])
app.include_router(templates.router, tags=["templates"])
app.include_router(bundles.router, tags=["bundles"])
app.include_router(analytics.router, tags=["analytics"])


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


# Lambda handler via Mangum
handler = Mangum(app, lifespan="off")
