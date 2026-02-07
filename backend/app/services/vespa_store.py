from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Mapping, Optional, Sequence

import httpx

from ..config import settings
from ..database.models import ProjectDocument

logger = logging.getLogger(__name__)


class VespaClientError(RuntimeError):
    pass


class VespaClient:
    def __init__(self, *, endpoint: str, namespace: str, document_type: str, rank_profile: str, timeout: float) -> None:
        self._base_url = endpoint.rstrip("/")
        self._namespace = namespace
        self._document_type = document_type
        self._rank_profile = rank_profile
        self._client = httpx.Client(timeout=timeout)

    def upsert_document(self, *, document_id: str, fields: Mapping[str, Any]) -> None:
        url = self._document_url(document_id)
        response = self._client.post(url, json={"fields": fields})
        self._raise_for_status(response, "upsert document")

    def delete_document(self, *, document_id: str) -> bool:
        url = self._document_url(document_id)
        response = self._client.delete(url)
        if response.status_code == 404:
            return False
        self._raise_for_status(response, "delete document")
        return True

    def search(
        self,
        *,
        project_id: str,
        embedding: Sequence[float],
        vector_k: int,
        top_k: int,
        weight_vector: float,
        weight_text: float,
        fts_query: Optional[str],
    ) -> List[Dict[str, Any]]:
        # Only include text search if fts_query is non-empty
        include_fts = bool(fts_query and fts_query.strip())
        yql = self._build_yql(project_id=project_id, vector_k=vector_k, include_text=include_fts)
        payload: Dict[str, Any] = {
            "yql": yql,
            "hits": top_k,
            "ranking": {
                "profile": self._rank_profile,
            },
            "presentation": {"summary": "default"},
            "input.query(query_embedding)": list(float(v) for v in embedding),
            "input.query(weight_vector)": weight_vector,
            "input.query(weight_text)": weight_text,
        }

        # For text search, use 'query' parameter with userQuery() function
        if include_fts:
            payload["query"] = fts_query

        response = self._client.post(f"{self._base_url}/search/", json=payload)
        self._raise_for_status(response, "search Vespa")
        data = response.json()
        hits = data.get("root", {}).get("children", []) or []
        results: List[Dict[str, Any]] = []
        for hit in hits:
            fields = hit.get("fields") or {}
            if not fields:
                continue
            results.append(fields)
        return results

    def _document_url(self, document_id: str) -> str:
        return f"{self._base_url}/document/v1/{self._namespace}/{self._document_type}/docid/{document_id}"

    def _build_yql(self, *, project_id: str, vector_k: int, include_text: bool) -> str:
        project_id_literal = self._yql_string_literal(project_id)
        base_filter = f"project_id contains {project_id_literal} AND active = true"
        vector_clause = f"{{targetHits:{max(1, vector_k)}}}nearestNeighbor(embedding, query_embedding)"
        if include_text:
            # Use OR operator for hybrid search: vector OR text
            # userQuery() reads from the 'query' parameter
            predicate = f"({vector_clause} OR userQuery())"
        else:
            predicate = vector_clause
        return f"select * from sources * where {base_filter} AND {predicate}"

    def _yql_string_literal(self, value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def _raise_for_status(self, response: httpx.Response, context: str) -> None:
        if response.status_code >= 400:
            detail = (response.text or "").strip()
            if len(detail) > 300:
                detail = f"{detail[:300]}..."
            logger.error("Vespa %s failed: %s", context, detail)
            suffix = f" - {detail}" if detail else ""
            raise VespaClientError(f"Failed to {context}: {response.status_code}{suffix}")


class VespaVectorStore:
    def __init__(self, *, project_id: str, client: VespaClient) -> None:
        self._project_id = project_id
        self._client = client
        self._vespa_dim = settings.vespa_embedding_dim

    def upsert_document(self, *, document: ProjectDocument, embedding: Sequence[float]) -> None:
        embedding_vector = self._normalise_embedding(embedding)
        fields = {
            "project_id": self._project_id,
            "document_id": document.id,
            "title": document.title,
            "content": document.content,
            "metadata": json.dumps(document.metadata_ or {}),
            "created_at": (document.created_at or document.updated_at).isoformat(),
            "active": document.active,
            "embedding": {"values": embedding_vector},
        }
        self._client.upsert_document(document_id=document.vespa_document_id, fields=fields)

    def delete_document(self, document: ProjectDocument) -> bool:
        return self._client.delete_document(document_id=document.vespa_document_id)

    def hybrid_search(
        self,
        *,
        embedding: Sequence[float],
        vector_k: int,
        top_k: int,
        weight_vector: float,
        weight_text: float,
        fts_query: Optional[str],
    ) -> List[Dict[str, Any]]:
        embedding_vector = self._normalise_embedding(embedding)
        return self._client.search(
            project_id=self._project_id,
            embedding=embedding_vector,
            vector_k=vector_k,
            top_k=top_k,
            weight_vector=weight_vector,
            weight_text=weight_text,
            fts_query=fts_query,
        )

    def _normalise_embedding(self, embedding: Sequence[float]) -> List[float]:
        values = [float(v) for v in embedding]
        if len(values) > self._vespa_dim:
            return values[: self._vespa_dim]
        if len(values) < self._vespa_dim:
            padding = [0.0] * (self._vespa_dim - len(values))
            return values + padding
        return values
