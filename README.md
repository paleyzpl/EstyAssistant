# Etsy Assistant

A web application and CLI tool for pen & ink sketch artists that turns sketch photos into print-ready digital downloads and publishes them to Etsy with AI-generated listings. Built for [Carrot Sketches](https://www.etsy.com/shop/CarrotSketches).

## Features

- **Image cleanup pipeline** — autocrop, perspective correction, background cleanup, contrast enhancement
- **Multi-size output** — resize to standard print sizes (5x7, 8x10, 11x14, 16x20, A4) at 300 DPI
- **AI listing generation** — Claude Vision analyzes your sketch and generates SEO-optimized titles, tags, and descriptions
- **Frame mockups** — composite your sketch into real photo frame templates for listing previews
- **Etsy integration** — OAuth 2.0 auth, draft listing creation, image & file upload via Etsy v3 API
- **Web UI** — drag-and-drop upload, before/after preview, inline listing editor, one-click Etsy publish
- **CLI** — batch process directories, generate listings, publish from the terminal

## Quick Start

### Web Application

```bash
# Backend (port 8000)
cd backend && uv sync --group dev
PYTHONPATH=../src:src uvicorn api.main:app --reload

# Frontend (port 3000)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000 — drop a sketch, pick sizes, process, generate listing, publish to Etsy.

### CLI

```bash
uv sync --group dev

# Process a single sketch
uv run etsy-assistant process sketch.jpg -s 8x10 -s 5x7

# Generate an Etsy listing (title, tags, description)
uv run etsy-assistant generate-listing sketch.jpg

# Full pipeline: process + listing + publish as Etsy draft
uv run etsy-assistant publish sketch.jpg -p 4.99
```

### Deploy

See [DEPLOY.md](DEPLOY.md) for full deployment instructions (AWS Lambda + Vercel).

## Architecture

```
CLI:  etsy-assistant process sketch.jpg -s 8x10
Web:  [Browser] → [Next.js on Vercel] → [API Gateway] → [FastAPI on Lambda] → [S3]
                                                                              → [Claude API]
                                                                              → [Etsy API]
Both use: src/etsy_assistant/ (shared core package)
```

## Pipeline Steps

| Step | Description |
|------|-------------|
| autocrop | Detect and crop to the paper region |
| perspective | Straighten using Hough line detection |
| background | Clean paper to pure white via adaptive thresholding |
| contrast | Enhance ink lines with CLAHE + levels normalization |

Skip any step with `--skip <step>` or `--no-perspective`.

## Testing

```bash
uv run pytest                                         # Core tests (87)
cd backend && PYTHONPATH=../src:src uv run pytest      # Backend tests (25)
cd frontend && npm run build                           # Frontend type check
```

## Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `ANTHROPIC_API_KEY` | Backend | Claude Vision listing generation |
| `ETSY_API_KEY` | Backend | Etsy OAuth + publishing |
| `S3_BUCKET` | Backend | Image storage bucket |
| `FRONTEND_URL` | Backend | OAuth callback redirect |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API URL |

## License

All rights reserved.
