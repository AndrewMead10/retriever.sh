from __future__ import annotations

import logging
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
            document = self._build_embedding_input(title=title, content=content)
        return self._embed(document, task_type="retrieval.passage")

    def embed_query(self, *, content: Sequence[Mapping[str, Any]]) -> Sequence[float]:
        with _logfire_span(
            "Build query embedding input",
            block_count=len(content),
        ):
            query_input = self._build_embedding_input(title="", content=content)
        return self._embed(query_input, task_type="retrieval.query")

    def _build_embedding_input(
        self, *, title: str, content: Sequence[Mapping[str, Any]]
    ) -> str | dict[str, Any]:
        text_blocks = [block for block in content if block.get("type") == "text"]
        if len(text_blocks) == len(content):
            text = "\n\n".join(str(block.get("text", "")).strip() for block in text_blocks).strip()
            return f"{title.strip()}\n\n{text}" if title.strip() else text

        blocks: list[dict[str, str]] = []
        if title.strip():
            blocks.append({"type": "text", "value": title.strip()})
        for block in content:
            blocks.append(self._to_provider_block(block))
        return {"content": blocks}

    def _to_provider_block(self, block: Mapping[str, Any]) -> dict[str, str]:
        block_type = block.get("type")
        if block_type == "text":
            return {"type": "text", "value": str(block.get("text", "")).strip()}

        if isinstance(block_type, str) and block_type.endswith("_url"):
            return {
                "type": self._provider_media_type(block_type),
                "format": "url",
                "value": str(block.get("url", "")).strip(),
            }

        if isinstance(block_type, str) and block_type.endswith("_base64"):
            provider_block = {
                "type": self._provider_media_type(block_type),
                "format": "base64",
                "value": str(block.get("data", "")).strip(),
            }
            media_type = block.get("media_type")
            if media_type:
                provider_block["media_type"] = str(media_type)
            return provider_block

        raise EmbeddingProviderError(f"Unsupported content block type: {block_type}")

    def _provider_media_type(self, block_type: str) -> str:
        if block_type.startswith("image_"):
            return "image"
        if block_type.startswith("audio_"):
            return "audio"
        if block_type.startswith("video_"):
            return "video"
        if block_type.startswith("file_"):
            return "file"
        raise EmbeddingProviderError(f"Unsupported content block type: {block_type}")

    def _embed(self, embedding_input: str | Mapping[str, Any], *, task_type: str) -> Sequence[float]:
        if not self._config.api_key:
            raise EmbeddingProviderError("RAG_EMBEDDING_API_KEY is not configured")

        with _logfire_span(
            "Remote embedding request",
            input_type="text" if isinstance(embedding_input, str) else "multimodal",
            target_dim=self._config.embed_dim,
            model_id=self._config.model_id,
            task_type=task_type,
        ):
            payload = {
                "input": [embedding_input],
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
