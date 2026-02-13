import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

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
        prompt = self._prompts.document.format(
            title=title.strip() or "none",
            text=text,
        )
        return self._embed(prompt)

    def embed_query(self, *, query: str) -> Sequence[float]:
        prompt = self._prompts.query.format(query=query)
        return self._embed(prompt)

    def _embed(self, prompt: str) -> Sequence[float]:
        with self._lock:
            vector = self._llama.embed(prompt)
        array = np.asarray(vector, dtype=np.float32)
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
