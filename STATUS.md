# Project Status

## Completed Phases

### Phase 1: Backend API
- FastAPI app with Mangum Lambda adapter
- `POST /process` — CV pipeline via S3 (bytes I/O)
- `GET /upload-url` — presigned S3 URLs for direct browser upload
- `POST /listing/generate` — Claude Vision metadata generation
- S3 helpers, Pydantic models, Dockerfile
- **PR #2** — merged

### Phase 2: Frontend Shell
- Next.js (App Router) with Tailwind CSS
- Drag-and-drop upload with S3 presigned URLs
- Print size selector (5x7, 8x10, 11x14, 16x20)
- Before/after image preview with download links
- Typed API client
- **PR #2** — merged

### Phase 3: AI Metadata + Listing Editor
- `POST /mockups/generate` endpoint with S3 storage
- ListingEditor component: editable title, tag chips, description
- MockupGallery component: frame mockup previews
- Bytes-based mockup generation in shared core
- **PR #4** — merged

### Phase 4: Etsy Integration
- Web-based OAuth 2.0 PKCE flow (replaces CLI local server)
- DynamoDB credential store for tokens + job tracking
- `POST /publish` — process + create Etsy draft + upload files
- `GET /jobs/{id}` — poll async job status
- Connect/disconnect UI with status indicator
- Publish section with price input and polling spinner
- OAuth callback page
- **PR #5** — merged

### Phase 5: Infrastructure & Deployment
- SAM template: Lambda (container), S3, DynamoDB, API Gateway
- `scripts/deploy-backend.sh` — one-command backend deploy
- `DEPLOY.md` — step-by-step guide from AWS account creation to running app
- Vercel config for frontend deployment
- **PR #3** — merged

## Test Coverage

| Suite | Tests | Location |
|-------|-------|----------|
| Core pipeline + CV steps | 87 | `tests/` |
| Backend API routes | 25 | `backend/tests/` |
| Frontend | Builds clean | `frontend/` |
| **Total** | **112** | |

## API Endpoints

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `GET` | `/health` | Health check | 1 |
| `GET` | `/upload-url` | Presigned S3 upload URL | 1 |
| `POST` | `/process` | Run CV pipeline | 1 |
| `POST` | `/listing/generate` | AI metadata via Claude Vision | 1 |
| `POST` | `/mockups/generate` | Frame mockup compositing | 3 |
| `GET` | `/auth/etsy/start` | Begin Etsy OAuth | 4 |
| `POST` | `/auth/etsy/callback` | Exchange OAuth code | 4 |
| `GET` | `/auth/etsy/status` | Check Etsy connection | 4 |
| `POST` | `/auth/etsy/disconnect` | Disconnect Etsy | 4 |
| `POST` | `/publish` | Process + create Etsy draft | 4 |
| `GET` | `/jobs/{id}` | Poll job status | 4 |

## Estimated Costs

| Service | Monthly Cost |
|---------|-------------|
| AWS Lambda + API Gateway | ~$0 (free tier) |
| S3 | ~$0.50 |
| DynamoDB | ~$0 (free tier) |
| Vercel | $0 (hobby) |
| Anthropic API | ~$0.05-0.10/image |
| **Total** | **~$1-5/month** |

### Listing History
- DynamoDB storage for saved listings
- Backend CRUD: `GET/POST /listings`, `GET/DELETE /listings/{id}`
- Frontend: collapsible history panel, save button, load into editor
- **PR #6** — open

## Future Work

- [ ] Batch processing in web UI — upload multiple sketches
- [ ] UI polish — loading toasts, mobile-responsive, dark mode
- [ ] Custom frame templates — upload your own mockup images
- [ ] Analytics — track listing performance
