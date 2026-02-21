from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.vespa_image_store import VespaImageStore
from app.services.vespa_store import VespaClient


def test_build_vector_only_yql_uses_project_filter():
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_image",
        rank_profile="rag-image",
        timeout=5.0,
    )

    yql = client._build_vector_only_yql(
        project_id="019c3671-5951-76ab-87fd-ba0e6045c63c",
        vector_k=10,
    )

    assert 'project_id contains "019c3671-5951-76ab-87fd-ba0e6045c63c"' in yql
    assert "AND ({targetHits:10}nearestNeighbor(embedding, query_embedding))" in yql


def test_vespa_image_embedding_dim_only_requires_positive(monkeypatch):
    monkeypatch.setattr(settings, "vespa_image_embedding_dim", 10)
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_image",
        rank_profile="rag-image",
        timeout=5.0,
    )
    store = VespaImageStore(project_id="project-1", client=client)
    assert store is not None


def test_vespa_image_embedding_dim_must_be_positive(monkeypatch):
    monkeypatch.setattr(settings, "vespa_image_embedding_dim", 0)
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_image",
        rank_profile="rag-image",
        timeout=5.0,
    )

    with pytest.raises(ValueError, match="greater than zero"):
        VespaImageStore(project_id="project-1", client=client)


def test_image_upsert_sends_expected_fields(monkeypatch):
    monkeypatch.setattr(settings, "vespa_image_embedding_dim", 8)

    class _CapturingClient:
        def __init__(self):
            self.document_id = None
            self.fields = None

        def upsert_document(self, *, document_id: str, fields):
            self.document_id = document_id
            self.fields = fields

    client = _CapturingClient()
    store = VespaImageStore(project_id="project-1", client=client)  # type: ignore[arg-type]
    image = SimpleNamespace(
        id=42,
        storage_key="projects/project-1/images/42/test.jpg",
        content_type="image/jpeg",
        metadata_={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        active=True,
        vespa_document_id="img-42",
    )

    store.upsert_image(image=image, embedding=[0.1, 0.2, -0.3, 0.4, 1.0, -2.0, 3.0, -4.0])

    assert client.document_id == "img-42"
    assert client.fields["storage_key"] == "projects/project-1/images/42/test.jpg"
    assert client.fields["content_type"] == "image/jpeg"
    assert "embedding" in client.fields
    assert client.fields["embedding"] == {"values": [0.1, 0.2, -0.3, 0.4, 1.0, -2.0, 3.0, -4.0]}


def test_image_search_uses_float_query_embedding(monkeypatch):
    monkeypatch.setattr(settings, "vespa_image_embedding_dim", 4)

    class _CapturingClient:
        def __init__(self):
            self.embedding = None
            self.vector_k = None
            self.top_k = None

        def search_vector_only_float(self, *, project_id: str, embedding, vector_k: int, top_k: int):
            self.embedding = embedding
            self.vector_k = vector_k
            self.top_k = top_k
            return []

    client = _CapturingClient()
    store = VespaImageStore(project_id="project-1", client=client)  # type: ignore[arg-type]
    store.search(embedding=[0.1, -0.2, 0.3, -0.4], vector_k=20, top_k=5)

    assert client.embedding == [0.1, -0.2, 0.3, -0.4]
    assert client.vector_k == 20
    assert client.top_k == 5
