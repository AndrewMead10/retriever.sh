from __future__ import annotations

import logging
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Sequence

import httpx

from ..config import settings

if settings.logfire_enabled:
    import logfire
else:
    logfire = None

logger = logging.getLogger(__name__)


class EmbeddingProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddingConfig:
    endpoint: str
    api_key: str
    model_id: str
    embed_dim: int
    timeout: float


class EmbeddingService:
    """Synchronous client for the remote OpenAI-compatible embedding service."""

    def __init__(self, config: EmbeddingConfig, client: httpx.Client | None = None) -> None:
        self._config = config
        self._base_url = config.endpoint.rstrip("/")
        self._client = client or httpx.Client(timeout=config.timeout)

    def embed_document(self, *, title: str, text: str) -> Sequence[float]:
        with _logfire_span(
            "Build document embedding input",
            title_length=len(title),
            text_length=len(text),
        ):
            document = f"{title.strip()}\n\n{text}" if title.strip() else text
        return self._embed(document, task_type="retrieval.passage")

    def embed_query(self, *, query: str) -> Sequence[float]:
        with _logfire_span(
            "Build text query embedding input",
            query_length=len(query),
        ):
            stripped_query = query.strip()
        return self._embed(stripped_query, task_type="retrieval.query")

    def _embed(self, text: str, *, task_type: str) -> Sequence[float]:
        if not self._config.api_key:
            raise EmbeddingProviderError("RAG_EMBEDDING_API_KEY is not configured")

        with _logfire_span(
            "Remote embedding request",
            text_length=len(text),
            target_dim=self._config.embed_dim,
            model_id=self._config.model_id,
            task_type=task_type,
        ):
            payload = {
                "input": text,
                "model": self._config.model_id,
                "encoding_format": "float",
                "dimensions": self._config.embed_dim,
                "task_type": task_type,
            }
            try:
                response = self._client.post(
                    f"{self._base_url}/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._config.api_key}"},
                    json=payload,
                )
            except httpx.HTTPError as exc:
                raise EmbeddingProviderError(f"Remote embedding request failed: {exc}") from exc

            if response.status_code >= 400:
                detail = _truncate_detail(response.text)
                logger.error("Remote embedding request failed: %s", detail)
                suffix = f" - {detail}" if detail else ""
                raise EmbeddingProviderError(
                    f"Remote embedding request failed: {response.status_code}{suffix}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise EmbeddingProviderError("Remote embedding response was not valid JSON") from exc

        return self._extract_embedding(data)

    def _extract_embedding(self, data: Any) -> Sequence[float]:
        try:
            embedding = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EmbeddingProviderError("Remote embedding response did not include an embedding") from exc

        if not isinstance(embedding, list):
            raise EmbeddingProviderError("Remote embedding response embedding was not a list")

        try:
            values = [float(value) for value in embedding]
        except (TypeError, ValueError) as exc:
            raise EmbeddingProviderError("Remote embedding response contained non-numeric values") from exc

        if len(values) != self._config.embed_dim:
            raise ValueError(
                f"Unexpected embedding dimension: expected {self._config.embed_dim}, got {len(values)}"
            )

        return values


def _truncate_detail(detail: str) -> str:
    stripped = (detail or "").strip()
    return f"{stripped[:300]}..." if len(stripped) > 300 else stripped


def _logfire_span(message_template: str, **attributes: int | str):
    if settings.logfire_enabled and logfire is not None:
        return logfire.span(message_template, **attributes)
    return nullcontext()
