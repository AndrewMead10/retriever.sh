from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from ..config import settings
from ..database.models import ProjectImage
from .vespa_store import VespaClient


class VespaImageStore:
    def __init__(self, *, project_id: str, client: VespaClient) -> None:
        self._project_id = project_id
        self._client = client
        self._source_dim = settings.vespa_image_embedding_dim
        if self._source_dim <= 0:
            raise ValueError("VESPA_IMAGE_EMBED_DIM must be greater than zero")

    def upsert_image(self, *, image: ProjectImage, embedding: Sequence[float]) -> None:
        embedding_vector = self._normalise_source_embedding(embedding)
        fields = {
            "project_id": self._project_id,
            "image_id": image.id,
            "storage_key": image.storage_key,
            "content_type": image.content_type,
            "metadata": json.dumps(image.metadata_ or {}),
            "created_at": (image.created_at or image.updated_at).isoformat(),
            "active": image.active,
            "embedding": {"values": embedding_vector},
        }
        self._client.upsert_document(document_id=image.vespa_document_id, fields=fields)

    def delete_image(self, image: ProjectImage) -> bool:
        return self._client.delete_document(document_id=image.vespa_document_id)

    def search(
        self,
        *,
        embedding: Sequence[float],
        vector_k: int,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        embedding_vector = self._normalise_source_embedding(embedding)
        return self._client.search_vector_only_float(
            project_id=self._project_id,
            embedding=embedding_vector,
            vector_k=vector_k,
            top_k=top_k,
        )

    def _normalise_source_embedding(self, embedding: Sequence[float]) -> List[float]:
        values = [float(v) for v in embedding]
        if len(values) > self._source_dim:
            return values[: self._source_dim]
        if len(values) < self._source_dim:
            padding = [0.0] * (self._source_dim - len(values))
            return values + padding
        return values
