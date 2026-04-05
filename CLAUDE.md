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

# Generate listing with AI metadata
uv run etsy-assistant generate-listing sketch.jpg --skip-processing
```

## Architecture

**Image Processing Pipeline** (`src/etsy_assistant/pipeline.py`):
Runs a sequential chain of CV steps on a sketch photo. Step order is fixed: `autocrop -> perspective -> background -> contrast`. Each step receives a numpy array (BGR) and `PipelineConfig`, returns transformed array. Steps can be skipped via `--skip`. After pipeline steps, `resize_for_print` produces size-specific outputs (5x7, 8x10, etc.).

**Pipeline Steps** (`src/etsy_assistant/steps/`):
- `autocrop.py` — detect and crop to the paper region
- `perspective.py` — straighten via Hough line detection
- `background.py` — clean paper background using adaptive thresholding
- `contrast.py` — enhance ink via CLAHE + floor/ceiling normalization
- `resize.py` — scale to standard print sizes at target DPI
- `output.py` — save with DPI metadata
- `keywords.py` — Claude Vision API call to generate title/tags/description as structured JSON

**Configuration** (`src/etsy_assistant/config.py`):
Single frozen dataclass `PipelineConfig` with all tunable parameters for every step. Supports `with_overrides()` for per-call customization.

**Etsy API Integration** (`src/etsy_assistant/etsy_api.py`):
OAuth 2.0 PKCE flow with local callback server. Handles token refresh automatically. Creates draft listings and uploads images/files via Etsy v3 API.

**CLI** (`src/etsy_assistant/cli.py`):
Click-based with commands: `process`, `batch`, `info`, `generate-listing`, `batch-listing`, `auth`, `publish`. The `publish` command chains the full pipeline: process -> AI metadata -> Etsy upload as draft.

**Templates** (`src/etsy_assistant/templates/`):
Room mockup templates (PNG images + JSON geometry data) for composite preview images.

## Testing

Tests use synthetic images (numpy arrays with drawn shapes) via fixtures in `conftest.py` — no real image files needed. The `ANTHROPIC_API_KEY` environment variable must be unset or mocked for tests that touch `keywords.py`.

## Key Constraints

- All CV operations use OpenCV (`cv2`) with BGR color order
- Images flow through the pipeline as `np.ndarray` (not PIL)
- Listing titles max 140 chars, tags max 13 items each max 20 chars
- Etsy digital file upload limit is 20 MB
- Credentials stored at `~/.etsy-assistant/credentials.json` with 0o600 permissions
- No git repository — this project is managed locally
