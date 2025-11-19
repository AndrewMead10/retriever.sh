from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from ..config import settings
from ..database.models import Project
from .vectorlab import EmbeddingConfig, EmbeddingService
from .vespa_store import VespaClient, VespaVectorStore


@dataclass(frozen=True)
class EmbeddingKey:
    provider: str
    model_repo: str
    model_file: str
    embed_dim: int


class VectorStoreRegistry:
    """Caches Vespa vector stores and shared embedding services."""

    def __init__(self) -> None:
        self._stores: Dict[int, VespaVectorStore] = {}
        self._embed_services: Dict[EmbeddingKey, EmbeddingService] = {}
        self._lock = threading.RLock()
        self._client = VespaClient(
            endpoint=settings.vespa_endpoint,
            namespace=settings.vespa_namespace,
            document_type=settings.vespa_document_type,
            rank_profile=settings.vespa_rank_profile,
            timeout=settings.vespa_timeout_seconds,
        )

    def get_vector_store(self, project: Project) -> VespaVectorStore:
        with self._lock:
            store = self._stores.get(project.id)
            if store is None:
                store = VespaVectorStore(project=project, client=self._client)
                self._stores[project.id] = store
            return store

    def _embedding_config(self, project: Project) -> EmbeddingConfig:
        model_repo = project.embedding_model_repo or settings.rag_model_repo
        model_file = project.embedding_model_file or settings.rag_model_filename

        return EmbeddingConfig(
            model_repo=model_repo,
            model_filename=model_file,
            model_dir=Path(settings.rag_model_dir),
            embed_dim=project.embedding_dim,
            hf_token=settings.rag_hf_token or None,
            llama_threads=settings.rag_llama_threads,
            llama_batch_size=settings.rag_llama_batch_size,
            llama_context=settings.rag_llama_context,
        )

    def get_embedder(self, project: Project) -> EmbeddingService:
        key = EmbeddingKey(
            provider=project.embedding_provider,
            model_repo=project.embedding_model_repo or settings.rag_model_repo,
            model_file=project.embedding_model_file or settings.rag_model_filename,
            embed_dim=project.embedding_dim,
        )
        with self._lock:
            embedder = self._embed_services.get(key)
            if embedder is None:
                config = self._embedding_config(project)
                embedder = EmbeddingService(config)
                self._embed_services[key] = embedder
            return embedder


vector_store_registry = VectorStoreRegistry()
