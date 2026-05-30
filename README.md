# retriever.sh

Production-ready FastAPI + React implementation that turns the original `vector-lab-rag` prototype into a multi-tenant product with plans, usage limits, Polar billing, and project-scoped vector stores.

## Highlights

- 🔐 **Self-service accounts** – email/password auth with JWT refresh, automatic account provisioning, and single-user billing ready for future org support.
- 🧱 **Project isolation** – each project stores its retrieval items in a shared Vespa content cluster filtered by `project_id`, so hybrid retrieval stays tenant-scoped without managing per-project tables.
- 🔎 **Multimodal retrieval** – Remote Jina omni embeddings and Vespa hybrid ranking power project-scoped search across text, images, audio, video, and PDFs.
- ⚖️ **Plan limits & rate enforcement** – token-bucket QPS limits (1 / 10 / 100 for Tinkering, Building, Scale) and plan-specific project/vector caps enforced entirely in PostgreSQL, no Redis required.
- 💳 **Polar integration** – plan checkout, self-service portal hand-off, and webhook handlers to activate subscriptions and keep limits in sync.
- 🌗 **Light/Dark UI** – React + TanStack Router frontend with Tailwind v4 theming, project dashboard, and one-click theme toggle.
- 🧪 **Targeted tests** – unit coverage for rate limiting and usage counters to guard quota logic.

## Quick Start

### 1. Configure Environment

```
cp .env.example .env
# fill in required secrets (JWT, Polar, etc.)
```

Key additions beyond the base template:

| Variable | Purpose |
| --- | --- |
| `RAG_EMBEDDING_BASE_URL` | Remote OpenAI-compatible embedding service base URL (default `https://embedding-server.amqm.dev`). |
| `RAG_EMBEDDING_API_KEY` | Bearer token for the remote embedding service. |
| `RAG_EMBEDDING_MODEL` | Remote embedding model ID (default `jinaai/jina-embeddings-v5-omni-small-retrieval`). |
| `RAG_EMBED_DIM` | Embedding dimension expected by Vespa (default `512`). |
| `RAG_EMBEDDING_TIMEOUT_SECONDS` | HTTP timeout for remote embedding requests (default `30`). |
| `POLAR_ACCESS_TOKEN` | Required for live checkout / portal creation (personal access token from Polar). |
| `POLAR_PRODUCT_TINKERING_ID` | Polar product ID for the Tinkering plan subscription. |
| `POLAR_PRODUCT_BUILDING_ID` | Polar product ID for the Building plan subscription. |
| `POLAR_PRODUCT_SCALE_ID` | Polar product ID for the Scale plan subscription. |
| `POLAR_SUCCESS_URL` / `POLAR_CANCEL_URL` | Post-checkout redirect destinations. |
| `POLAR_WEBHOOK_SECRET` | Signing secret from the Polar dashboard used to validate webhooks. |
| `POLAR_PORTAL_RETURN_URL` | Return destination after closing the Polar customer portal. |

### 2. Backend

```
cd backend
pip install uv
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 5656
```

Run Vespa so hybrid retrieval has a live content cluster before ingesting data:

```
docker compose up -d vespa
vespa deploy --wait 300 vespa
```

On startup the app seeds the canonical plans (Tinkering / Building / Scale) and ensures rate-limit buckets exist for each account.

### 3. Frontend

```
cd frontend
npm install
npm run dev
```

Vite runs at `http://localhost:3000` and proxies `/api` to the backend on port 5656.

For production builds, run `npm run build` from `frontend/`. The compiled assets are written directly to `backend/app/static` so the FastAPI server can serve the SPA.

### 4. Production Deployment

Production deploys through GitHub Actions in `.github/workflows/deploy.yml`.

On pushes to `main`, the workflow:
- runs backend tests and frontend typecheck
- builds the Docker image, including frontend static assets
- pushes the image to GitHub Container Registry
- SSHes to `root@178.156.219.85`
- syncs `docker-compose.yml`, `scripts/deploy-vespa.sh`, and `vespa/`
- pulls the new backend image
- starts PostgreSQL and Vespa
- deploys the Vespa application package
- runs `alembic upgrade head`
- starts/restarts the backend container

Required GitHub secrets:
- `DEPLOY_SSH_PRIVATE_KEY`: private key for SSH access to `root@178.156.219.85`
- `GHCR_TOKEN`: token with package read permission if the GHCR package is private
- `GHCR_USERNAME`: username for the GHCR token
- `APP_DATABASE_URL`: optional; defaults to the Docker Compose PostgreSQL service URL

The deployment host must keep its production `.env` at `/root/retriever.sh/.env`.

### 5. Polar Webhooks (optional)

Configure a tunnel (ngrok, Cloudflare, etc.) and add the forwarded URL as a webhook endpoint in the Polar dashboard, pointing to `http://localhost:5656/api/billing/webhook`.

## API Overview

### Project Management (auth required)

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/projects/onload` | Returns plan info, usage counters, and project summaries for the signed-in user. |
| `POST` | `/api/projects/onsubmit` | Creates a project and returns the initial ingest API key (only shown once). |

Each project record stores embedding settings, vector store path, and summary counts. The frontend surfaces these details along with upgrade CTAs.

### Retrieval API (project key required)

Use the `X-Project-Key` header with the value returned on project creation (or subsequent key rotations).

#### Ingest item

```
POST /api/rag/projects/{project_id}/items
X-Project-Key: proj_...
{
  "title": "Product launch brief",
  "content": [
    {
      "type": "text",
      "text": "Launch messaging and product visuals."
    },
    {
      "type": "image_url",
      "url": "https://example.com/product.png"
    }
  ],
  "metadata": {
    "source": "launch-drive",
    "category": "marketing"
  },
  "external_id": "launch-brief-2026"
}
```

- Counts toward ingestion QPS and vector totals.
- Supports `text`, `image_url`, `image_base64`, `audio_url`, `audio_base64`, `video_url`, `video_base64`, `file_url`, and `file_base64` content blocks. File blocks are for PDFs; there is no separate file-upload API.
- Enforces vector-cap before inserting into the Vespa corpus and mirrors metadata in PostgreSQL (`project_documents`) so item IDs stay stable.

#### Hybrid query

```
POST /api/rag/projects/{project_id}/query
X-Project-Key: proj_...
{
  "input": [
    {
      "type": "text",
      "text": "find the product launch brief"
    }
  ],
  "top_k": 5
}
```

Returns the weighted hybrid ranking powered by Vespa's `rag-hybrid` profile. Query inputs can use the same text/image/audio/video/PDF content block shape as ingest. Requests consume the plan-specific query QPS bucket.

#### Delete item

```
DELETE /api/rag/projects/{project_id}/items/{item_id}
X-Project-Key: proj_...
```

Removes the item from Vespa (keyword + ANN indexes), soft-deletes it in PostgreSQL, and decrements usage counters so customers can free capacity.

### Billing Endpoints (auth required)

| Method | Endpoint | Notes |
| --- | --- | --- |
| `POST` | `/api/billing/portal` | Generates a Polar customer portal session for self-service management. |
| `POST` | `/api/billing/webhook` | Processes checkout completions and subscription lifecycle events (Polar forwards checkout metadata with `account_id`). |

If Polar credentials are omitted the endpoints fail fast with HTTP 503 so development can proceed without billing configured.

## Usage Limits

Plan seeding defines the default caps:

| Plan | Monthly Price | Query QPS | Ingest QPS | Projects | Vector cap (per project) |
| --- | --- | --- | --- | --- | --- |
| Tinkering | $5 | 1 | 1 | 3 | 10,000 |
| Building | $20 | 10 | 10 | 20 | 100,000 |
| Scale | $50 | 100 | 100 | Unlimited | 250,000 |

- QPS is enforced with token buckets stored in PostgreSQL (`rate_limit_buckets`).
- Every plan enforces its vector cap on a per-project basis using the `plans.vector_limit` value.
- Item vectors count toward the per-project vector cap.
- Vector/storage caps are defined per plan and scale only when you switch tiers.
- Limit errors return 402/429 with an upsell message so the frontend can surface upgrade prompts.

## Tests

Backend unit tests cover quota enforcement:

```
cd backend
uv run pytest backend/tests/test_rate_limits.py
```

The suite verifies token-bucket behaviour and vector-cap checks. Additonal integration tests can build upon these fixtures.

## Frontend Overview

- `/` – marketing-style landing page with quick links.
- `/projects` – primary control panel showing plan usage, upgrade actions, and project list with create dialog.
- Light/dark theme toggle persists in `localStorage` and respects OS defaults.

## Developer Notes

- Plan records are seeded at startup via `seed_plans`; change defaults there for future migrations.
- Item metadata is stored in PostgreSQL; Vespa holds the `rag_document` embedding index scoped by `project_id`.
- Polar webhooks rely on Checkout metadata containing `account_id`; ensure the checkout metadata set during session creation matches this expectation.
- Multimodal embeddings are generated by the remote OpenAI-compatible embedding server; the backend no longer loads a local model.

## License

See [LICENSE](./LICENSE) for details.
