from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.vespa_store import VespaClient, VespaVectorStore


def test_build_yql_uses_string_filter_for_uuid_project_id():
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_document",
        rank_profile="rag-hybrid",
        timeout=5.0,
    )

    yql = client._build_yql(
        project_id="019c3671-5951-76ab-87fd-ba0e6045c63c",
        vector_k=20,
        include_text=True,
    )

    assert 'project_id contains "019c3671-5951-76ab-87fd-ba0e6045c63c"' in yql
    assert "{targetHits:20}nearestNeighbor(embedding, query_embedding)" in yql
    assert "OR userQuery()" in yql


def test_build_yql_without_text_wraps_nearest_neighbor_clause():
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_document",
        rank_profile="rag-hybrid",
        timeout=5.0,
    )

    yql = client._build_yql(
        project_id="019c3671-5951-76ab-87fd-ba0e6045c63c",
        vector_k=20,
        include_text=False,
    )

    assert "AND ({targetHits:20}nearestNeighbor(embedding, query_embedding))" in yql


def test_search_sends_float_query_embedding(monkeypatch):
    monkeypatch.setattr(settings, "vespa_embedding_dim", 8)

    class _CapturingClient(VespaClient):
        def __init__(self):
            super().__init__(
                endpoint="http://localhost:8080",
                namespace="rag",
                document_type="rag_document",
                rank_profile="rag-hybrid",
                timeout=5.0,
            )
            self.payload = None

        def _execute_search(self, payload):
            self.payload = payload
            return []

    client = _CapturingClient()
    store = VespaVectorStore(project_id="project-1", client=client)

    store.hybrid_search(
        embedding=[0.1, -0.2, 0.3, -0.4, 0.5, -0.6, 0.7, -0.8],
        vector_k=20,
        top_k=5,
        weight_vector=0.7,
        weight_text=0.3,
        fts_query=None,
    )

    assert client.payload["input.query(query_embedding)"] == [0.1, -0.2, 0.3, -0.4, 0.5, -0.6, 0.7, -0.8]


def test_vespa_embedding_dim_must_be_positive(monkeypatch):
    monkeypatch.setattr(settings, "vespa_embedding_dim", 0)
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_document",
        rank_profile="rag-hybrid",
        timeout=5.0,
    )
    with pytest.raises(ValueError, match="greater than zero"):
        VespaVectorStore(project_id="project-1", client=client)


def test_embedding_dimension_mismatch_raises(monkeypatch):
    monkeypatch.setattr(settings, "vespa_embedding_dim", 8)
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_document",
        rank_profile="rag-hybrid",
        timeout=5.0,
    )
    store = VespaVectorStore(project_id="project-1", client=client)

    with pytest.raises(ValueError, match="Expected embedding dimension 8, got 3"):
        store._normalise_source_embedding([0.1, 0.2, 0.3])


def test_upsert_sends_float_embedding_field(monkeypatch):
    monkeypatch.setattr(settings, "vespa_embedding_dim", 8)

    class _CapturingClient:
        def __init__(self):
            self.document_id = None
            self.fields = None

        def upsert_document(self, *, document_id: str, fields):
            self.document_id = document_id
            self.fields = fields

    client = _CapturingClient()
    store = VespaVectorStore(project_id="project-1", client=client)  # type: ignore[arg-type]
    doc = SimpleNamespace(
        id=42,
        title="t",
        content="c",
        metadata_={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        active=True,
        vespa_document_id="doc-42",
    )

    store.upsert_document(document=doc, embedding=[0.1, 0.2, -0.3, 0.4, 1.0, -2.0, 3.0, -4.0])

    assert client.document_id == "doc-42"
    assert "embedding" in client.fields
    assert client.fields["embedding"] == {"values": [0.1, 0.2, -0.3, 0.4, 1.0, -2.0, 3.0, -4.0]}


def test_execute_search_sorts_rows_by_relevance_descending():
    class _Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "root": {
                    "children": [
                        {"relevance": 0.15, "fields": {"document_id": 10, "title": "third"}},
                        {"relevance": 0.95, "fields": {"document_id": 11, "title": "first"}},
                        {"relevance": "0.60", "fields": {"document_id": 12, "title": "second"}},
                    ]
                }
            }

    class _Client:
        @staticmethod
        def post(url: str, json):
            return _Response()

    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_document",
        rank_profile="rag-hybrid",
        timeout=5.0,
    )
    client._client = _Client()  # type: ignore[assignment]

    rows = client._execute_search({"yql": "select * from sources * where true"})

    assert [row["document_id"] for row in rows] == [11, 12, 10]
    assert [row["_vespa_relevance"] for row in rows] == [0.95, 0.6, 0.15]
