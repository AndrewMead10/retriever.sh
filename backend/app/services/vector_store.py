from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from ..config import settings
from ..database.models import Project
from .siglip2_embeddings import Siglip2Config, Siglip2EmbeddingService
from .vectorlab import EmbeddingConfig, EmbeddingService
from .vespa_image_store import VespaImageStore
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
        self._stores: Dict[str, VespaVectorStore] = {}
        self._image_stores: Dict[str, VespaImageStore] = {}
        self._embed_services: Dict[EmbeddingKey, EmbeddingService] = {}
        self._image_embedder: Siglip2EmbeddingService | None = None
        self._lock = threading.RLock()
        self._client = VespaClient(
            endpoint=settings.vespa_endpoint,
            namespace=settings.vespa_namespace,
            document_type=settings.vespa_document_type,
            rank_profile=settings.vespa_rank_profile,
            timeout=settings.vespa_timeout_seconds,
        )
        self._image_client = VespaClient(
            endpoint=settings.vespa_endpoint,
            namespace=settings.vespa_namespace,
            document_type=settings.vespa_image_document_type,
            rank_profile=settings.vespa_image_rank_profile,
            timeout=settings.vespa_timeout_seconds,
        )

    def get_vector_store(self, project: Project) -> VespaVectorStore:
        project_id = str(project.id)
        with self._lock:
            store = self._stores.get(project_id)
            if store is None:
                store = VespaVectorStore(project_id=project_id, client=self._client)
                self._stores[project_id] = store
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

    def _image_embedding_config(self) -> Siglip2Config:
        return Siglip2Config(
            model_id=settings.rag_image_model_id,
            model_dir=Path(settings.rag_image_model_dir),
            embed_dim=settings.rag_image_embed_dim,
            device=settings.rag_image_device,
            dtype=settings.rag_image_dtype,
            hf_token=settings.rag_hf_token or None,
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

    def get_image_vector_store(self, project: Project) -> VespaImageStore:
        project_id = str(project.id)
        with self._lock:
            store = self._image_stores.get(project_id)
            if store is None:
                store = VespaImageStore(project_id=project_id, client=self._image_client)
                self._image_stores[project_id] = store
            return store

    def get_image_embedder(self) -> Siglip2EmbeddingService:
        with self._lock:
            if self._image_embedder is None:
                config = self._image_embedding_config()
                self._image_embedder = Siglip2EmbeddingService(config)
            return self._image_embedder


vector_store_registry = VectorStoreRegistry()
