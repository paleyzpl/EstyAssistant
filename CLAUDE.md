# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Etsy Assistant is a CLI tool for pen & ink sketch artists that processes sketch photos into print-ready digital downloads and generates optimized Etsy listing metadata using Claude Vision. The shop is "Carrot Sketches."

## Development Setup

This project uses **uv** for dependency management with Python 3.12+.

```bash
uv sync --group dev          # Install all dependencies including dev
uv run etsy-assistant --help  # Run the CLI
```

## Common Commands

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_autocrop.py

# Run a specific test
uv run pytest tests/test_autocrop.py::test_name -v

# Process a single image
uv run etsy-assistant process sketch.jpg -s 8x10 -s 5x7

# Batch process a directory
uv run etsy-assistant batch ./sketches/ -o ./output/ -s 8x10 -s 5x7

# Generate listing with AI metadata
uv run etsy-assistant generate-listing sketch.jpg --skip-processing

# Full publish pipeline (process -> AI metadata -> Etsy draft)
uv run etsy-assistant publish sketch.jpg -s 8x10 -s 5x7 -p 4.99

# Authenticate with Etsy
uv run etsy-assistant auth --api-key YOUR_KEY
```

## Architecture

### Image Processing Pipeline (`src/etsy_assistant/pipeline.py`)

Runs a sequential chain of CV steps on a sketch photo. Step order is fixed: `autocrop -> perspective -> background -> contrast` (defined in `STEP_ORDER`). Each step is a pure function receiving `(np.ndarray, PipelineConfig)` and returning a transformed array. Steps can be skipped via `--skip`. The pipeline continues on step failure (logs exception, uses previous result). After pipeline steps, `resize_for_print` produces size-specific outputs.

### Pipeline Steps (`src/etsy_assistant/steps/`)

- `autocrop.py` — detect and crop to the paper region using edge detection + contour finding
- `perspective.py` — correct perspective via 4-point transform; falls back to Hough line rotation deskewing
- `background.py` — clean paper background to white using adaptive thresholding + morphological operations
- `contrast.py` — enhance ink via CLAHE + floor/ceiling normalization + gamma correction
- `resize.py` — scale to standard print sizes (5x7, 8x10, 11x14, 16x20, A4) at target DPI; respects aspect ratio and orientation
- `output.py` — save as PNG with DPI metadata via PIL/Pillow
- `keywords.py` — Claude Vision API call to generate title/tags/description as structured JSON (default model: `claude-sonnet-4-20250514`)
- `mockup.py` — composite processed sketch into frame template mockups; auto-detects frame interior, matches orientation

### Configuration (`src/etsy_assistant/config.py`)

Single frozen dataclass `PipelineConfig` with all tunable parameters for every step (autocrop thresholds, perspective Hough params, background adaptive block size, contrast CLAHE settings, output DPI/format). Supports `with_overrides()` for per-call customization.

### Etsy API Integration (`src/etsy_assistant/etsy_api.py`)

OAuth 2.0 PKCE flow with local callback server. Handles token refresh automatically on 401 responses. Creates draft listings and uploads images/files via Etsy v3 API. Listing defaults: digital download type, taxonomy ID 1 (Art & Collectibles > Prints), who_made="i_did", quantity=999999.

### CLI (`src/etsy_assistant/cli.py`)

Click-based with 7 commands: `process`, `batch`, `info`, `generate-listing`, `batch-listing`, `auth`, `publish`. The `publish` command chains the full pipeline: process -> AI metadata -> Etsy upload as draft. Supports `--dry-run` for testing without Etsy upload.

### Templates (`src/etsy_assistant/templates/`)

Room mockup templates (JPEG images + `templates.json` geometry data) for composite preview images. Three templates included: light wood frame, styled wood frame with candle, black frame on rattan dresser. All current templates are vertical orientation.

### Memory (`memory/`)

Project context and user feedback logs (Markdown files) documenting shop preferences, listing style, and workflow notes.

## Testing

Tests use synthetic images (numpy arrays with drawn shapes) via fixtures in `conftest.py` — no real image files needed. The `ANTHROPIC_API_KEY` environment variable must be unset or mocked for tests that touch `keywords.py`.

Test files cover all major components:
- `test_autocrop.py` — border removal, content preservation, fallback handling
- `test_background.py` — adaptive thresholding and morphological cleanup
- `test_contrast.py` — CLAHE + levels + gamma + sharpening
- `test_perspective.py` — 4-point transform and rotation deskewing
- `test_resize.py` — print size scaling, aspect ratio, orientation
- `test_pipeline.py` — end-to-end processing, multi-size, skip-steps, debug mode
- `test_keywords.py` — Claude Vision API integration, JSON parsing, metadata save/load
- `test_etsy_api.py` — OAuth flow, token refresh, listing creation, uploads (mocked HTTP)

## Key Constraints

- All CV operations use OpenCV (`cv2`) with BGR color order
- Images flow through the pipeline as `np.ndarray` (not PIL); convert to RGB only for final save
- Pipeline steps are stateless pure functions: `(np.ndarray, PipelineConfig) -> np.ndarray`
- Listing titles max 140 chars, tags max 13 items each max 20 chars
- Etsy digital file upload limit is 20 MB
- Supported print sizes: 5x7, 8x10, 11x14, 16x20, A4 (8.27x11.69 inches)
- Default output DPI is 300
- Credentials stored at `~/.etsy-assistant/credentials.json` with 0o600 permissions
- No CI/CD pipeline — local development only

## Dependencies

**Production:** opencv-python-headless (>=4.9), Pillow (>=10.0), numpy (>=1.26), click (>=8.1), anthropic (>=0.40), httpx (>=0.27)

**Dev:** pytest (>=8.0)

**Build:** hatchling
