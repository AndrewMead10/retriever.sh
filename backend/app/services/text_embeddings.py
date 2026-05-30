from __future__ import annotations

import logging
import math
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

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

    def embed_item(self, *, title: str, content: Sequence[Mapping[str, Any]]) -> Sequence[float]:
        with _logfire_span(
            "Build item embedding input",
            title_length=len(title),
            block_count=len(content),
        ):
            document = self._build_embedding_inputs(title=title, content=content)
        return self._embed(document, task_type="retrieval.passage")

    def embed_query(self, *, content: Sequence[Mapping[str, Any]]) -> Sequence[float]:
        with _logfire_span(
            "Build query embedding input",
            block_count=len(content),
        ):
            query_input = self._build_embedding_inputs(title="", content=content)
        return self._embed(query_input, task_type="retrieval.query")

    def _build_embedding_inputs(
        self, *, title: str, content: Sequence[Mapping[str, Any]]
    ) -> list[str]:
        text_blocks = [block for block in content if block.get("type") == "text"]
        text = "\n\n".join(str(block.get("text", "")).strip() for block in text_blocks).strip()
        text_input = f"{title.strip()}\n\n{text}" if title.strip() and text else title.strip() or text

        inputs: list[str] = []
        if text_input:
            inputs.append(text_input)
        for block in content:
            if block.get("type") != "text":
                inputs.append(self._to_provider_input(block))
        return inputs

    def _to_provider_input(self, block: Mapping[str, Any]) -> str:
        block_type = block.get("type")
        if block_type == "text":
            return str(block.get("text", "")).strip()

        if isinstance(block_type, str) and block_type.endswith("_url"):
            return str(block.get("url", "")).strip()

        if isinstance(block_type, str) and block_type.endswith("_base64"):
            media_type = block.get("media_type")
            data = str(block.get("data", "")).strip()
            if not media_type:
                raise EmbeddingProviderError(f"Missing media_type for content block type: {block_type}")
            return f"data:{media_type};base64,{data}"

        raise EmbeddingProviderError(f"Unsupported content block type: {block_type}")

    def _embed(self, embedding_inputs: Sequence[str], *, task_type: str) -> Sequence[float]:
        if not self._config.api_key:
            raise EmbeddingProviderError("RAG_EMBEDDING_API_KEY is not configured")
        if not embedding_inputs:
            raise EmbeddingProviderError("Embedding input was empty")

        with _logfire_span(
            "Remote embedding request",
            input_count=len(embedding_inputs),
            target_dim=self._config.embed_dim,
            model_id=self._config.model_id,
            task_type=task_type,
        ):
            payload = {
                "input": list(embedding_inputs),
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

        return self._combine_embeddings(self._extract_embeddings(data))

    def _extract_embeddings(self, data: Any) -> list[Sequence[float]]:
        try:
            rows = data["data"]
        except (KeyError, TypeError) as exc:
            raise EmbeddingProviderError("Remote embedding response did not include an embedding") from exc

        if not isinstance(rows, list) or not rows:
            raise EmbeddingProviderError("Remote embedding response did not include an embedding")

        embeddings: list[Sequence[float]] = []
        for row in rows:
            try:
                embedding = row["embedding"]
            except (KeyError, TypeError) as exc:
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
            embeddings.append(values)

        return embeddings

    def _combine_embeddings(self, embeddings: Sequence[Sequence[float]]) -> Sequence[float]:
        if len(embeddings) == 1:
            return list(embeddings[0])

        combined = [
            sum(embedding[index] for embedding in embeddings) / len(embeddings)
            for index in range(self._config.embed_dim)
        ]
        norm = math.sqrt(sum(value * value for value in combined))
        if norm == 0:
            return combined
        return [value / norm for value in combined]


def _truncate_detail(detail: str) -> str:
    stripped = (detail or "").strip()
    return f"{stripped[:300]}..." if len(stripped) > 300 else stripped


def _logfire_span(message_template: str, **attributes: int | str):
    if settings.logfire_enabled and logfire is not None:
        return logfire.span(message_template, **attributes)
    return nullcontext()
