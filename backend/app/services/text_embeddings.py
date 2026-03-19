import logging
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from ..config import settings

if settings.logfire_enabled:
    import logfire
else:
    logfire = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingConfig:
    model_repo: str
    model_filename: str
    model_dir: Path
    embed_dim: int
    hf_token: str | None = None
    llama_threads: int = 4
    llama_batch_size: int = 8
    llama_context: int = 2048

    @property
    def model_path(self) -> Path:
        return self.model_dir / self.model_filename


@dataclass(frozen=True)
class EmbeddingPrompts:
    """Prompt templates used before invoking llama.cpp embeddings."""

    document: str = "search_document: {text}"
    query: str = "search_query: {query}"


class EmbeddingService:
    """Wrapper around llama.cpp embeddings for synchronous usage."""

    def __init__(self, config: EmbeddingConfig, prompts: EmbeddingPrompts | None = None) -> None:
        self._config = config
        self._prompts = prompts or EmbeddingPrompts()
        self._model_path = self._ensure_model_file(config)
        self._llama = self._load_model(self._model_path, config)
        self._lock = threading.RLock()

    def embed_document(self, *, title: str, text: str) -> Sequence[float]:
        with _logfire_span(
            "Build document embedding prompt",
            title_length=len(title),
            text_length=len(text),
        ):
            prompt = self._prompts.document.format(
                title=title.strip() or "none",
                text=text,
            )
        return self._embed(prompt)

    def embed_query(self, *, query: str) -> Sequence[float]:
        with _logfire_span(
            "Build text query embedding prompt",
            query_length=len(query),
        ):
            prompt = self._prompts.query.format(query=query)
        return self._embed(prompt)

    def _embed(self, prompt: str) -> Sequence[float]:
        with _logfire_span(
            "llama.cpp embedding pipeline",
            prompt_length=len(prompt),
            target_dim=self._config.embed_dim,
        ):
            with _logfire_span("Run llama.cpp embed inference"):
                with self._lock:
                    vector = self._llama.embed(prompt)
            with _logfire_span("Convert raw embedding to float32 array"):
                array = np.asarray(vector, dtype=np.float32)
            with _logfire_span(
                "Validate and adjust embedding dimensions",
                source_dim=int(array.shape[0]),
                target_dim=self._config.embed_dim,
            ):
                if array.shape[0] < self._config.embed_dim:
                    raise ValueError(
                        f"Unexpected embedding dimension: expected at least {self._config.embed_dim}, got {array.shape[0]}"
                    )
                if array.shape[0] > self._config.embed_dim:
                    # Nomic embeddings are Matryoshka-capable: keep the leading dimensions.
                    return array[: self._config.embed_dim]
                return array

    def _load_model(self, model_path: Path, config: EmbeddingConfig) -> Llama:
        return Llama(
            model_path=str(model_path),
            embedding=True,
            n_ctx=config.llama_context,
            n_threads=config.llama_threads,
            n_batch=config.llama_batch_size,
        )

    def _ensure_model_file(self, config: EmbeddingConfig) -> Path:
        config.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = config.model_path
        if model_path.exists():
            logger.info("Using existing GGUF model at %s", model_path)
            return model_path

        logger.info(
            "Downloading model %s from %s into %s",
            config.model_filename,
            config.model_repo,
            config.model_dir,
        )
        hf_hub_download(
            repo_id=config.model_repo,
            filename=config.model_filename,
            local_dir=str(config.model_dir),
            local_dir_use_symlinks=False,
            token=config.hf_token,
        )
        if not model_path.exists():
            raise FileNotFoundError(f"expected model file at {model_path} after download")
        return model_path


def _logfire_span(message_template: str, **attributes: int):
    if settings.logfire_enabled and logfire is not None:
        return logfire.span(message_template, **attributes)
    return nullcontext()
