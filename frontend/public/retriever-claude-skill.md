# retriever.sh - Claude Code Skill

## Overview

retriever.sh is a simple, powerful search API with just three core functions:
1. **SEARCH** - Find relevant documents using semantic search
2. **ADD** - Add documents to your knowledge base
3. **DELETE** - Remove documents from your knowledge base

## Configuration

### Required Environment Variables

When building applications that use retriever.sh, ensure the user has set:

```bash
RETRIEVER_API_KEY=rs_live_your_api_key_here
```

Users can obtain their API key from the retriever.sh projects page after signing up.

### API Base URL

```
https://api.retriever.sh
```

## API Reference

### 1. SEARCH - Find Relevant Documents

Search through indexed documents using semantic and full-text search.

**Endpoint:** `POST /v1/search`

**Headers:**
```
Authorization: Bearer {RETRIEVER_API_KEY}
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "your search terms",
  "limit": 10,
  "filters": {
    "category": "optional_category",
    "custom_field": "optional_value"
  }
}
```

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, optional, default: 10): Maximum number of results to return
- `filters` (object, optional): Metadata filters to apply to the search

**Response:**
```json
{
  "results": [
    {
      "id": "doc_123",
      "title": "Document Title",
      "content": "Relevant excerpt from the document...",
      "score": 0.95,
      "metadata": {
        "category": "tutorial",
        "custom_field": "value"
      }
    }
  ],
  "total": 1,
  "query_time": 0.045
}
```

**When to Use:**
- User asks a question that requires domain-specific knowledge
- Need to retrieve context from a knowledge base
- Looking for relevant documentation or information
- Performing semantic search across indexed content

**Example Usage:**
```python
import requests
import os

def search_knowledge_base(query: str) -> dict:
    response = requests.post(
        "https://api.retriever.sh/v1/search",
        headers={
            "Authorization": f"Bearer {os.getenv('RETRIEVER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={"query": query, "limit": 5}
    )
    return response.json()

# Usage in a conversation
results = search_knowledge_base("How do I configure authentication?")
for result in results["results"]:
    print(f"Found: {result['title']}")
    print(f"Content: {result['content']}\n")
```

### 2. ADD - Add Documents to Knowledge Base

Add or update documents in the search index.

**Endpoint:** `POST /v1/documents`

**Headers:**
```
Authorization: Bearer {RETRIEVER_API_KEY}
Content-Type: application/json
```

**Request Body:**
```json
{
  "documents": [
    {
      "id": "unique_doc_id",
      "title": "Document Title",
      "content": "Full document content to be indexed and searched...",
      "metadata": {
        "category": "tutorial",
        "author": "John Doe",
        "custom_field": "any value"
      }
    }
  ]
}
```

**Parameters:**
- `documents` (array, required): Array of document objects to add/update
  - `id` (string, required): Unique identifier for the document
  - `title` (string, required): Document title
  - `content` (string, required): Full text content to be indexed
  - `metadata` (object, optional): Custom metadata fields for filtering

**Response:**
```json
{
  "count": 1,
  "status": "success",
  "indexed_ids": ["unique_doc_id"]
}
```

**When to Use:**
- User wants to add new information to their knowledge base
- Indexing documentation or content for future retrieval
- Updating existing documents with new information
- Building a searchable knowledge repository

**Example Usage:**
```python
import requests
import os

def add_documents(docs: list) -> dict:
    response = requests.post(
        "https://api.retriever.sh/v1/documents",
        headers={
            "Authorization": f"Bearer {os.getenv('RETRIEVER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={"documents": docs}
    )
    return response.json()

# Usage
new_docs = [
    {
        "id": "install_guide_001",
        "title": "Python Installation Guide",
        "content": "To install Python on your system...",
        "metadata": {"category": "tutorial", "language": "python"}
    }
]
result = add_documents(new_docs)
print(f"Successfully indexed {result['count']} documents")
```

### 3. DELETE - Remove Documents

Delete documents from the knowledge base.

**Endpoint:** `DELETE /v1/documents/{document_id}`

**Headers:**
```
Authorization: Bearer {RETRIEVER_API_KEY}
```

**URL Parameters:**
- `document_id` (string, required): The unique ID of the document to delete

**Response:**
```json
{
  "success": true,
  "deleted_id": "doc_123"
}
```

**When to Use:**
- User wants to remove outdated information
- Deleting incorrect or deprecated documents
- Cleaning up the knowledge base
- Removing specific documents by ID

**Example Usage:**
```python
import requests
import os

def delete_document(doc_id: str) -> dict:
    response = requests.delete(
        f"https://api.retriever.sh/v1/documents/{doc_id}",
        headers={
            "Authorization": f"Bearer {os.getenv('RETRIEVER_API_KEY')}"
        }
    )
    return response.json()

# Usage
result = delete_document("install_guide_001")
if result["success"]:
    print(f"Successfully deleted document: {result['deleted_id']}")
```
