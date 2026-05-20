# retriever.sh - Claude Code Skill

## Overview

retriever.sh exposes project-scoped document retrieval APIs:

- Ingest: `POST /api/rag/projects/{project_id}/documents`
- Query: `POST /api/rag/projects/{project_id}/query`
- Delete: `DELETE /api/rag/projects/{project_id}/vectors/{document_id}`

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

### 1. INGEST - Add a Document

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

### 2. QUERY - Hybrid Text Search

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

### 3. DELETE - Remove a Document Vector

**Endpoint:** `DELETE /api/rag/projects/{project_id}/vectors/{document_id}`

**Headers:**
```text
X-Project-Key: {RETRIEVER_PROJECT_KEY}
```

## Minimal Python Example

```python
import os
import requests

project_id = os.environ["RETRIEVER_PROJECT_ID"]
project_key = os.environ["RETRIEVER_PROJECT_KEY"]

results = requests.post(
    f"https://retriever.sh/api/rag/projects/{project_id}/query",
    headers={"X-Project-Key": project_key, "Content-Type": "application/json"},
    json={"query": "shipping policy", "top_k": 5},
    timeout=30,
)
results.raise_for_status()

print(results.json().get("results", []))
```

## Error Handling

- `400`: invalid payload
- `401`: missing or invalid `X-Project-Key`
- `404`: project or document not found
- `429`: query/ingest QPS rate limit exceeded
- `402`: plan capacity/limit reached

Always parse and surface the response `detail` field.
