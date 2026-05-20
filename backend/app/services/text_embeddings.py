import logging
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

from ..config import settings

if settings.logfire_enabled:
    import logfire
else:
    logfire = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingConfig:
    model_id: str
    model_dir: Path
    embed_dim: int
    hf_token: str | None = None
    device: str = "cpu"


@dataclass(frozen=True)
class EmbeddingPrompts:
    """Prompt names configured by the DenseOn Sentence Transformers model."""

    document: str = "document"
    query: str = "query"


class EmbeddingService:
    """Wrapper around Sentence Transformers embeddings for synchronous usage."""

    def __init__(self, config: EmbeddingConfig, prompts: EmbeddingPrompts | None = None) -> None:
        self._config = config
        self._prompts = prompts or EmbeddingPrompts()
        self._model = self._load_model(config)
        self._lock = threading.RLock()

    def embed_document(self, *, title: str, text: str) -> Sequence[float]:
        with _logfire_span(
            "Build document embedding prompt",
            title_length=len(title),
            text_length=len(text),
        ):
            document = f"{title.strip()}\n\n{text}" if title.strip() else text
        return self._embed(document, prompt_name=self._prompts.document)

    def embed_query(self, *, query: str) -> Sequence[float]:
        with _logfire_span(
            "Build text query embedding prompt",
            query_length=len(query),
        ):
            stripped_query = query.strip()
        return self._embed(stripped_query, prompt_name=self._prompts.query)

    def _embed(self, text: str, *, prompt_name: str) -> Sequence[float]:
        with _logfire_span(
            "Sentence Transformers embedding pipeline",
            text_length=len(text),
            target_dim=self._config.embed_dim,
            model_id=self._config.model_id,
        ):
            with _logfire_span("Run Sentence Transformers encode inference"):
                with self._lock:
                    vector = self._model.encode(
                        [text],
                        prompt_name=prompt_name,
                        normalize_embeddings=True,
                        convert_to_numpy=True,
                    )
            with _logfire_span("Convert raw embedding to float32 array"):
                array = np.asarray(vector, dtype=np.float32)
                if array.ndim == 2:
                    array = array[0]
            with _logfire_span(
                "Validate embedding dimensions",
                source_dim=int(array.shape[0]),
                target_dim=self._config.embed_dim,
            ):
                if array.ndim != 1:
                    raise ValueError(f"Expected 1D embedding vector, got shape {tuple(array.shape)}")
                if array.shape[0] != self._config.embed_dim:
                    raise ValueError(
                        f"Unexpected embedding dimension: expected {self._config.embed_dim}, got {array.shape[0]}"
                    )
                return array

    def _load_model(self, config: EmbeddingConfig) -> SentenceTransformer:
        config.model_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Loading Sentence Transformers model %s", config.model_id)
        kwargs = {
            "cache_folder": str(config.model_dir),
            "device": config.device,
        }
        if config.hf_token:
            kwargs["token"] = config.hf_token
        return SentenceTransformer(
            config.model_id,
            **kwargs,
        )


def _logfire_span(message_template: str, **attributes: int | str):
    if settings.logfire_enabled and logfire is not None:
        return logfire.span(message_template, **attributes)
    return nullcontext()
