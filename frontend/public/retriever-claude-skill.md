# retriever.sh - Claude Code Skill

## Overview

retriever.sh exposes project-scoped multimodal retrieval APIs:

- Ingest: `POST /api/rag/projects/{project_id}/items`
- Query: `POST /api/rag/projects/{project_id}/query`
- Delete: `DELETE /api/rag/projects/{project_id}/items/{item_id}`

All operations require:
- `project_id` in the URL path
- `Authorization: Bearer <api_key>` header for that project

Project IDs and keys are available in the retriever.sh Projects page.

## Configuration

### Required Environment Variables

```bash
RETRIEVER_PROJECT_ID=your-project-uuid
RETRIEVER_PROJECT_KEY=retr_proj_...your_key...
```

### API Base URL

```text
https://retriever.sh
```

## Content Blocks

Use the same typed block shape for item `content` and query `input`:

- `{"type": "text", "text": "..."}`
- `{"type": "image_url", "url": "https://..."}`
- `{"type": "image_base64", "data": "...", "media_type": "image/png"}`
- `{"type": "audio_url", "url": "https://..."}`
- `{"type": "audio_base64", "data": "...", "media_type": "audio/mpeg"}`
- `{"type": "video_url", "url": "https://..."}`
- `{"type": "video_base64", "data": "...", "media_type": "video/mp4"}`
- `{"type": "file_url", "url": "https://...", "media_type": "application/pdf"}`
- `{"type": "file_base64", "data": "...", "media_type": "application/pdf"}`

There is no separate file-upload endpoint.

## API Reference

### 1. INGEST - Add an Item

**Endpoint:** `POST /api/rag/projects/{project_id}/items`

**Headers:**
```text
Authorization: Bearer {RETRIEVER_PROJECT_KEY}
Content-Type: application/json
```

**Request Body:**
```json
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
  "date": "2026-05-30T00:00:00Z",
  "external_id": "launch-brief-2026"
}
```

`date` is an optional application-level timestamp for range search. It is separate from Retriever's `created_at` ingest timestamp.

### 2. QUERY - Hybrid Multimodal Search

**Endpoint:** `POST /api/rag/projects/{project_id}/query`

**Headers:**
```text
Authorization: Bearer {RETRIEVER_PROJECT_KEY}
Content-Type: application/json
```

**Request Body:**
```json
{
  "input": [
    {
      "type": "text",
      "text": "Find the launch brief with this product image"
    },
    {
      "type": "image_url",
      "url": "https://example.com/reference.png"
    }
  ],
  "top_k": 5,
  "vector_k": 40,
  "date_from": "2026-05-01T00:00:00Z",
  "date_to": "2026-05-31T23:59:59Z"
}
```

`date_from` and `date_to` are optional inclusive filters against the item `date` field.

### 3. DELETE - Remove an Item

**Endpoint:** `DELETE /api/rag/projects/{project_id}/items/{item_id}`

**Headers:**
```text
Authorization: Bearer {RETRIEVER_PROJECT_KEY}
```

## Minimal Python Example

```python
import os
import requests

project_id = os.environ["RETRIEVER_PROJECT_ID"]
project_key = os.environ["RETRIEVER_PROJECT_KEY"]

results = requests.post(
    f"https://retriever.sh/api/rag/projects/{project_id}/query",
    headers={"Authorization": f"Bearer {project_key}", "Content-Type": "application/json"},
    json={
        "input": [{"type": "text", "text": "shipping policy"}],
        "top_k": 5,
        "date_from": "2026-01-01T00:00:00Z",
    },
    timeout=30,
)
results.raise_for_status()

print(results.json().get("results", []))
```

## Error Handling

- `400`: invalid payload
- `401`: missing or invalid project API key
- `404`: project or item not found
- `429`: query/ingest QPS rate limit exceeded
- `402`: plan capacity/limit reached

Always parse and surface the response `detail` field.
