# retriever.sh

Production-ready FastAPI + React implementation that turns the original `vector-lab-rag` prototype into a multi-tenant product with plans, usage limits, Polar billing, and project-scoped vector stores.

## Highlights

- 🔐 **Self-service accounts** – email/password auth with JWT refresh, automatic account provisioning, and single-user billing ready for future org support.
- 🧱 **Project isolation** – each project provisions its own pgvector-backed namespace while reusing the hybrid retrieval logic from `vector-lab-rag`.
- ⚖️ **Plan limits & rate enforcement** – token-bucket QPS limits (1/10 for Free, 25/100 for Pro) and vector caps enforced entirely in PostgreSQL, no Redis required.
- 💳 **Polar integration** – checkout session generation for upgrades and vector top-ups, portal hand-off, and webhook handlers to activate plans/add capacity.
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
| `RAG_MODEL_REPO` / `RAG_MODEL_FILENAME` | Hugging Face repo + GGUF file for embeddings (defaults to the nomic model from `vector-lab-rag`). |
| `RAG_EMBED_DIM` | Embedding dimension expected by the model (default `768`). |
| `POLAR_ACCESS_TOKEN` | Required for live checkout / portal creation (personal access token from Polar). |
| `POLAR_PRODUCT_PRO_ID` | Polar product ID for the subscription upgrade. |
| `POLAR_PRODUCT_TOPUP_ID` | Polar product ID for one-off vector top-ups. |
| `POLAR_TOPUP_UNIT_CENTS` | Amount (in cents) charged per million vectors purchased. |
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

On startup the app seeds the canonical plans (free / pro / scale) and ensures rate-limit buckets exist for each account.

### 3. Frontend

```
cd frontend
npm install
npm run dev
```

Vite runs at `http://localhost:3000` and proxies `/api` to the backend on port 5656.

### 4. Polar Webhooks (optional)

Configure a tunnel (ngrok, Cloudflare, etc.) and add the forwarded URL as a webhook endpoint in the Polar dashboard, pointing to `http://localhost:5656/api/billing/webhook`.

## API Overview

### Project Management (auth required)

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/projects/onload` | Returns plan info, usage counters, and project summaries for the signed-in user. |
| `POST` | `/api/projects/onsubmit` | Creates a project and returns the initial ingest API key (only shown once). |

Each project record stores embedding settings, vector store path, and summary counts. The frontend surfaces these details along with upgrade/top-up CTAs.

### Retrieval API (project key required)

Use the `X-Project-Key` header with the value returned on project creation (or subsequent key rotations).

#### Ingest document

```
POST /api/rag/projects/{project_id}/documents
X-Project-Key: proj_...
{
  "title": "Doc title",
  "text": "Full text",
  "url": "https://example.com",
  "published_at": "2025-10-27T00:00:00Z"
}
```

- Counts toward ingestion QPS and vector totals.
- Enforces vector-cap before inserting into the project pgvector namespace.

#### Hybrid query

```
POST /api/rag/projects/{project_id}/query
X-Project-Key: proj_...
{
  "query": "what did we promise",
  "top_k": 5
}
```

Returns the weighted hybrid ranking identical to the original `vector-lab-rag` results. Requests consume the plan-specific query QPS bucket.

#### Delete vector

```
DELETE /api/rag/projects/{project_id}/vectors/{document_id}
X-Project-Key: proj_...
```

Removes the document from FTS, vector index, and decrements usage counters so customers can free capacity.

### Billing Endpoints (auth required)

| Method | Endpoint | Notes |
| --- | --- | --- |
| `POST` | `/api/billing/upgrade` | Creates a Polar Checkout session for the Pro plan. |
| `POST` | `/api/billing/topup` | Expects `{"quantity_millions": 1}`; opens Checkout for one-off vector bundles. |
| `POST` | `/api/billing/portal` | Generates a Polar customer portal session for self-service management. |
| `POST` | `/api/billing/scale` | Captures “contact us” requests for the enterprise plan. |
| `POST` | `/api/billing/webhook` | Processes checkout completions and subscription lifecycle events (Polar forwards checkout metadata with `account_id`). |

If Polar credentials are omitted the endpoints fail fast with HTTP 503 so development can proceed without billing configured.

## Usage Limits

Plan seeding defines the default caps:

| Plan | Monthly Price | Query QPS | Ingest QPS | Projects | Vector cap |
| --- | --- | --- | --- | --- | --- |
| Free | $0 | 1 | 10 | 3 | 1,000 |
| Pro | $10 | 25 | 100 | Unlimited | 1,000,000 + paid top-ups |
| Scale | Contact | 250 | 1000 | Unlimited | 10,000,000 (negotiable) |

- QPS is enforced with token buckets stored in PostgreSQL (`rate_limit_buckets`).
- Vector/storage caps combine the base plan limit plus any purchased top-ups.
- Limit errors return 402/429 with an upsell message so the frontend can surface upgrade prompts.

## Testing

Backend unit tests cover quota enforcement:

```
cd backend
uv run pytest backend/tests/test_rate_limits.py
```

The suite verifies token-bucket behaviour and vector-cap checks. Additonal integration tests can build upon these fixtures.

## Frontend Overview

- `/` – marketing-style landing page with quick links.
- `/projects` – primary control panel showing plan usage, upgrade/top-up actions, and project list with create dialog.
- `/dashboard` – legacy metrics view retained from the template.
- Light/dark theme toggle persists in `localStorage` and respects OS defaults.

## Developer Notes

- Plan records are seeded at startup via `seed_plans`; change defaults there for future migrations.
- Project creation initialises a dedicated pgvector table (`rag_documents_proj_<id>`) for hybrid search.
- Polar webhooks rely on Checkout metadata containing `account_id`; ensure the checkout metadata set during session creation matches this expectation.
- The vector embedding model downloads on-demand using `huggingface_hub` and `llama-cpp-python`. Provide `RAG_HF_TOKEN` if the repo is gated.

## License

See [LICENSE](./LICENSE) for details.
