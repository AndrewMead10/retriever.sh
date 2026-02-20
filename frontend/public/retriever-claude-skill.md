# retriever.sh - Claude Code Skill

## Overview

retriever.sh exposes project-scoped retrieval APIs across two search spaces:

1. **Text search space** (documents)
- Ingest: `POST /api/rag/projects/{project_id}/documents`
- Query: `POST /api/rag/projects/{project_id}/query`
- Delete: `DELETE /api/rag/projects/{project_id}/vectors/{document_id}`

2. **Image search space** (SigLIP2 + R2)
- Ingest image: `POST /api/rag/projects/{project_id}/images`
- Query by text: `POST /api/rag/projects/{project_id}/images/query/text`
- Query by image: `POST /api/rag/projects/{project_id}/images/query/image`
- Delete image: `DELETE /api/rag/projects/{project_id}/images/{image_id}`

All operations require:
- `project_id` in the URL path
- `X-Project-Key` header for that project

Project IDs and keys are available in the retriever.sh Projects page.

## Configuration

### Required Environment Variables

```bash
RETRIEVER_PROJECT_ID=your-project-uuid
RETRIEVER_PROJECT_KEY=proj_...your_key...
```

### API Base URL

```text
https://retriever.sh
```

## API Reference

### Text Search Space

#### 1. INGEST - Add a Document

**Endpoint:** `POST /api/rag/projects/{project_id}/documents`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Python Installation Guide",
  "text": "To install Python, visit python.org...",
  "metadata": {
    "source": "https://python.org/downloads/",
    "category": "docs"
  }
}
```

#### 2. QUERY - Hybrid Text Search

**Endpoint:** `POST /api/rag/projects/{project_id}/query`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "How do I install Python?",
  "top_k": 5,
  "vector_k": 40
}
```

#### 3. DELETE - Remove a Document Vector

**Endpoint:** `DELETE /api/rag/projects/{project_id}/vectors/{document_id}`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
```

### Image Search Space

Images are stored in Cloudflare R2 and indexed with SigLIP2 embeddings.

#### 4. INGEST IMAGE - Upload + Index

**Endpoint:** `POST /api/rag/projects/{project_id}/images`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
Content-Type: multipart/form-data
```

**Form fields:**
- `image` (required, binary)
- `metadata` (optional, JSON string)

**cURL Example:**
```bash
curl -X POST "https://retriever.sh/api/rag/projects/${RETRIEVER_PROJECT_ID}/images" \
  -H "X-Project-Key: ${RETRIEVER_PROJECT_KEY}" \
  -F 'metadata={"category":"product","source":"catalog"}' \
  -F 'image=@./photo.jpg;type=image/jpeg'
```

#### 5. QUERY IMAGE BY TEXT

**Endpoint:** `POST /api/rag/projects/{project_id}/images/query/text`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "red running shoes on white background",
  "top_k": 5,
  "vector_k": 50
}
```

#### 6. QUERY IMAGE BY IMAGE

**Endpoint:** `POST /api/rag/projects/{project_id}/images/query/image`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
Content-Type: multipart/form-data
```

**Form fields:**
- `image` (required, binary)
- `top_k` (optional)
- `vector_k` (optional)

**cURL Example:**
```bash
curl -X POST "https://retriever.sh/api/rag/projects/${RETRIEVER_PROJECT_ID}/images/query/image" \
  -H "X-Project-Key: ${RETRIEVER_PROJECT_KEY}" \
  -F 'top_k=5' \
  -F 'vector_k=50' \
  -F 'image=@./query.jpg;type=image/jpeg'
```

#### 7. DELETE IMAGE

**Endpoint:** `DELETE /api/rag/projects/{project_id}/images/{image_id}`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
```

## Minimal Python Example

```python
import json
import os
import requests

project_id = os.environ["RETRIEVER_PROJECT_ID"]
project_key = os.environ["RETRIEVER_PROJECT_KEY"]

# Text query
text_results = requests.post(
    f"https://retriever.sh/api/rag/projects/{project_id}/query",
    headers={"X-Project-Key": project_key, "Content-Type": "application/json"},
    json={"query": "shipping policy", "top_k": 5},
    timeout=30,
)
text_results.raise_for_status()

# Image query by text
image_results = requests.post(
    f"https://retriever.sh/api/rag/projects/{project_id}/images/query/text",
    headers={"X-Project-Key": project_key, "Content-Type": "application/json"},
    json={"query": "black backpack on a studio backdrop", "top_k": 5},
    timeout=30,
)
image_results.raise_for_status()

print(text_results.json().get("results", []))
print(image_results.json().get("results", []))
```

## Error Handling

- `400`: invalid payload (including bad image metadata JSON)
- `401`: missing or invalid `X-Project-Key`
- `404`: project/document/image not found
- `413`: uploaded image exceeds configured size limit
- `429`: query/ingest QPS rate limit exceeded
- `402`: plan capacity/limit reached

Always parse and surface the response `detail` field.
