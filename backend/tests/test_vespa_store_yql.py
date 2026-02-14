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


def test_pack_embedding_bits_uses_signed_big_endian_bit_packing(monkeypatch):
    monkeypatch.setattr(settings, "vespa_embedding_dim", 8)
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_document",
        rank_profile="rag-hybrid",
        timeout=5.0,
    )
    store = VespaVectorStore(project_id="project-1", client=client)

    packed = store._pack_embedding_bits([0.5, -0.1, 0.0, 9.2, 3.4, -2.0, 8.1, -7.0])

    # Positive => 1, non-positive => 0, then packed MSB first:
    # 10011010 (154 unsigned) => -102 signed int8.
    assert packed == [-102]


def test_vespa_embedding_dim_must_be_divisible_by_eight(monkeypatch):
    monkeypatch.setattr(settings, "vespa_embedding_dim", 10)
    client = VespaClient(
        endpoint="http://localhost:8080",
        namespace="rag",
        document_type="rag_document",
        rank_profile="rag-hybrid",
        timeout=5.0,
    )

    with pytest.raises(ValueError, match="divisible by 8"):
        VespaVectorStore(project_id="project-1", client=client)
