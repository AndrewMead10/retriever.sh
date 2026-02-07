from app.services.vespa_store import VespaClient


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
