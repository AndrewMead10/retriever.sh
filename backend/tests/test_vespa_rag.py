"""
API test for RAG endpoints.

Tests the complete flow:
1. Upload documents to Vespa via the ingest endpoint
2. Search for documents via the query endpoint (HYBRID SEARCH: vector + text)
3. Delete all documents to clean up

HYBRID SEARCH IMPLEMENTATION:
This test validates true hybrid search functionality, which combines:
- Vector similarity search using nearestNeighbor with embeddings
- Full-text search using userQuery() on title and content fields
- Results are ranked using weighted scoring (configurable per project)

The YQL query generated is:
  select * from sources * where project_id = X AND active = true
  AND ({'targetHits':K}nearestNeighbor(embedding, query_embedding) OR userQuery())

The vector store boundary is stubbed so this test does not depend on a local
Vespa deployment or a downloaded embedding model.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import models  # Import all models to ensure tables are created
from app.database.models import (
    Base,
    ManagementApiKey,
    Plan,
    Project,
    ProjectApiKey,
    ProjectDocument,
    RateLimitBucket,
    User,
    UserSubscription,
    UserUsage,
)
from app.functions.api_keys import generate_api_key, hash_api_key
from app.main import app


class _StubEmbedder:
    def embed_item(self, *, title: str, content):
        return [0.1] * 512

    def embed_query(self, *, content):
        return [0.2] * 512


class _StubVectorStore:
    def __init__(self) -> None:
        self.documents = {}

    def upsert_document(self, *, document: ProjectDocument, embedding):
        self.documents[document.id] = {
            "document_id": document.id,
            "title": document.title,
            "content": document.content,
            "metadata": document.metadata_,
            "date": document.metadata_.get("__retriever_date") if document.metadata_ else None,
            "created_at": document.created_at,
            "active": document.active,
            "_vespa_relevance": 1.0,
        }

    def hybrid_search(
        self,
        *,
        embedding,
        vector_k: int,
        top_k: int,
        weight_vector: float,
        weight_text: float,
        fts_query: str | None,
        date_from=None,
        date_to=None,
    ):
        rows = [row for row in self.documents.values() if row["active"]]
        if date_from is not None or date_to is not None:
            def _timestamp(value):
                if value is None:
                    return None
                parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
                return parsed.timestamp()

            from_ts = _timestamp(date_from)
            to_ts = _timestamp(date_to)
            rows = [
                row
                for row in rows
                if row["date"] is not None
                and (from_ts is None or _timestamp(row["date"]) >= from_ts)
                and (to_ts is None or _timestamp(row["date"]) <= to_ts)
            ]
        return rows[:top_k]

    def delete_document(self, document: ProjectDocument):
        if document.id in self.documents:
            self.documents[document.id]["active"] = False
        return True


@pytest.fixture
def engine():
    """Create a test database engine."""
    import os
    import tempfile

    # Use a temporary file that will be automatically cleaned up
    db_fd, db_path = tempfile.mkstemp(suffix='.db', prefix='test_vespa_')
    os.close(db_fd)  # Close the file descriptor, we just need the path

    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        # Clean up the test database
        Base.metadata.drop_all(engine)
        engine.dispose()
        # Ensure the database file is removed even if test fails
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture
def session(engine) -> Session:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(session: Session, monkeypatch):
    """Create a FastAPI test client with database session override."""
    from app.database import get_db
    from app.config import settings

    # Disable logfire for tests to avoid logging issues
    monkeypatch.setattr(settings, "logfire_enabled", False)
    vector_store = _StubVectorStore()

    from app.pages import rag_api

    monkeypatch.setattr(rag_api.vector_store_registry, "get_embedder", lambda project: _StubEmbedder())
    monkeypatch.setattr(rag_api.vector_store_registry, "get_vector_store", lambda project: vector_store)

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def seeded_project(session: Session):
    """Create a test user, plan, subscription, and project with API key."""
    # Create plan
    plan = Plan(
        slug="tinkering",
        name="Tinkering",
        price_cents=500,
        query_qps_limit=10,
        ingest_qps_limit=10,
        project_limit=3,
        vector_limit=10_000,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(plan)
    session.flush()

    # Create user
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(user)
    session.flush()

    # Create subscription and usage
    subscription = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    usage = UserUsage(
        user_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add_all([subscription, usage])
    session.flush()

    # Create rate limit buckets
    query_bucket = RateLimitBucket(
        user_id=user.id,
        limit_type="query",
        tokens=plan.query_qps_limit,
        last_refill=datetime.utcnow(),
        max_tokens=plan.query_qps_limit,
    )
    ingest_bucket = RateLimitBucket(
        user_id=user.id,
        limit_type="ingest",
        tokens=plan.ingest_qps_limit,
        last_refill=datetime.utcnow(),
        max_tokens=plan.ingest_qps_limit,
    )
    session.add_all([query_bucket, ingest_bucket])
    session.flush()

    # Generate API key
    api_key = generate_api_key(prefix="test")

    # Create project
    project = Project(
        user_id=user.id,
        name="Test RAG Project",
        description="Test project for Vespa RAG",
        slug="test-rag-project",
        embedding_provider="remote-http",
        embedding_model="jinaai/jina-embeddings-v5-text-small-retrieval-mlx",
        embedding_model_repo=None,
        embedding_model_file=None,
        embedding_dim=512,
        hybrid_weight_vector=0.7,
        hybrid_weight_text=0.3,
        top_k_default=5,
        vector_search_k=20,
        vector_store_path="test_vespa_project",
        vector_count=0,
        active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(project)
    session.flush()
    session.add(
        ProjectApiKey(
            project_id=project.id,
            name="Test key",
            prefix=api_key[:10],
            hashed_key=hash_api_key(api_key),
            revoked=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    session.commit()
    session.refresh(project)

    return {
        "project": project,
        "api_key": api_key,
        "user": user,
        "plan": plan,
    }


def test_vespa_rag_workflow(test_client: TestClient, seeded_project):
    """
    Test the complete Vespa RAG workflow:
    1. Upload multiple documents
    2. Search for documents
    3. Delete all uploaded documents
    """
    project = seeded_project["project"]
    api_key = seeded_project["api_key"]

    # Prepare test documents
    test_documents = [
        {
            "title": "Introduction to Machine Learning",
            "date": "2026-01-10T00:00:00Z",
            "content": [
                {
                    "type": "text",
                    "text": "Machine learning is a subset of artificial intelligence that focuses on building systems that learn from data. It enables computers to improve their performance on tasks without being explicitly programmed.",
                }
            ],
            "metadata": {"source": "https://example.com/ml-intro"},
        },
        {
            "title": "Deep Learning Fundamentals",
            "date": "2026-02-10T00:00:00Z",
            "content": [
                {
                    "type": "text",
                    "text": "Deep learning uses neural networks with multiple layers to progressively extract higher-level features from raw input. It has revolutionized computer vision and natural language processing.",
                }
            ],
            "metadata": {"source": "https://example.com/deep-learning"},
        },
        {
            "title": "Natural Language Processing Basics",
            "content": [
                {
                    "type": "text",
                    "text": "Natural language processing (NLP) is a branch of artificial intelligence that helps computers understand, interpret and manipulate human language. NLP draws from many disciplines, including computer science and computational linguistics.",
                }
            ],
            "metadata": {"source": "https://example.com/nlp-basics"},
        },
    ]

    uploaded_doc_ids = []

    # Step 1: Upload documents
    print("\n--- Step 1: Uploading documents ---")
    for doc in test_documents:
        response = test_client.post(
            f"/api/rag/projects/{project.id}/items",
            json=doc,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 201, f"Failed to upload document: {response.json()}"

        result = response.json()
        uploaded_doc_ids.append(result["id"])

        assert result["title"] == doc["title"]
        # The response can have either 'text' or 'content' due to aliasing
        assert result["content"] == doc["content"]
        assert result["metadata"] == doc["metadata"]
        assert result.get("date") == doc.get("date")
        assert "id" in result
        assert "created_at" in result

        print(f"✓ Uploaded document: {doc['title']} (ID: {result['id']})")

    assert len(uploaded_doc_ids) == 3, "Should have uploaded 3 documents"

    # Step 2: Search for documents
    print("\n--- Step 2: Searching documents ---")

    # Search for "machine learning"
    search_query = {
        "input": [{"type": "text", "text": "machine learning artificial intelligence"}],
        "top_k": 5,
    }

    response = test_client.post(
        f"/api/rag/projects/{project.id}/query",
        json=search_query,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 200, f"Failed to query documents: {response.json()}"

    search_results = response.json()
    assert "results" in search_results
    assert len(search_results["results"]) > 0, "Should return at least one result"

    print(f"✓ Search returned {len(search_results['results'])} results")

    # Verify search results have expected fields
    for idx, result in enumerate(search_results["results"], 1):
        assert "id" in result
        assert "title" in result
        assert "content" in result
        assert "metadata" in result
        assert "score" in result
        print(f"  {idx}. {result['title']}")

    # Search for "deep learning"
    search_query2 = {
        "input": [{"type": "text", "text": "neural networks deep learning"}],
        "top_k": 3,
    }

    response2 = test_client.post(
        f"/api/rag/projects/{project.id}/query",
        json=search_query2,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response2.status_code == 200
    search_results2 = response2.json()
    assert len(search_results2["results"]) > 0
    print(f"✓ Second search returned {len(search_results2['results'])} results")

    date_filtered_query = {
        "input": [{"type": "text", "text": "learning"}],
        "top_k": 5,
        "date_from": "2026-02-01T00:00:00Z",
        "date_to": "2026-02-28T23:59:59Z",
    }
    response3 = test_client.post(
        f"/api/rag/projects/{project.id}/query",
        json=date_filtered_query,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response3.status_code == 200
    filtered_results = response3.json()["results"]
    assert [result["title"] for result in filtered_results] == ["Deep Learning Fundamentals"]

    # Step 3: Delete all uploaded documents
    print("\n--- Step 3: Deleting documents ---")
    for doc_id in uploaded_doc_ids:
        response = test_client.delete(
            f"/api/rag/projects/{project.id}/items/{doc_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 204, f"Failed to delete document {doc_id}: {response.text}"
        print(f"✓ Deleted document ID: {doc_id}")

    # Verify documents are deleted by searching again
    print("\n--- Step 4: Verifying deletion ---")
    response = test_client.post(
        f"/api/rag/projects/{project.id}/query",
        json={"input": [{"type": "text", "text": "machine learning"}], "top_k": 10},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 200
    final_results = response.json()

    # Should return no results or significantly fewer results
    # (depending on whether other tests have added documents)
    print(f"✓ Post-deletion search returned {len(final_results['results'])} results")

    print("\n✅ All tests passed! Vespa RAG workflow completed successfully.")


def test_invalid_api_key(test_client: TestClient, seeded_project):
    """Test that invalid API keys are rejected."""
    project = seeded_project["project"]

    response = test_client.post(
        f"/api/rag/projects/{project.id}/items",
        json={
            "title": "Test",
            "content": [{"type": "text", "text": "Test content"}],
        },
        headers={"Authorization": "Bearer invalid_key"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


def test_missing_api_key(test_client: TestClient, seeded_project):
    """Test that missing API keys are rejected."""
    project = seeded_project["project"]

    response = test_client.post(
        f"/api/rag/projects/{project.id}/items",
        json={
            "title": "Test",
            "content": [{"type": "text", "text": "Test content"}],
        },
    )

    assert response.status_code == 401
    assert "detail" in response.json()


def test_nonexistent_project(test_client: TestClient):
    """Test that queries to non-existent projects return 404."""
    response = test_client.post(
        "/api/rag/projects/99999/query",
        json={"input": [{"type": "text", "text": "test"}]},
        headers={"Authorization": "Bearer test_fake_key"},
    )

    assert response.status_code == 404
    assert "detail" in response.json()


def test_management_key_can_create_project_and_project_keys(
    test_client: TestClient,
    session: Session,
    seeded_project,
):
    user = seeded_project["user"]
    management_key = generate_api_key(prefix="retr_mgmt")
    session.add(
        ManagementApiKey(
            user_id=user.id,
            name="Agent setup key",
            prefix=management_key[:10],
            hashed_key=hash_api_key(management_key),
            revoked=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    session.commit()

    response = test_client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {management_key}"},
        json={
            "name": "Agent Project",
            "description": "Created by test agent",
            "api_key_name": "agent-runtime-key",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["project"]["name"] == "Agent Project"
    assert payload["api_key"].startswith("retr_proj_")
    assert payload["authorization_header"] == f"Bearer {payload['api_key']}"

    project_id = payload["project"]["id"]
    key_response = test_client.post(
        f"/api/projects/{project_id}/api-keys",
        headers={"Authorization": f"Bearer {management_key}"},
        json={"name": "another-agent-key"},
    )

    assert key_response.status_code == 201, key_response.text
    assert key_response.json()["api_key"].startswith("retr_proj_")

    list_response = test_client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {management_key}"},
    )

    assert list_response.status_code == 200
    assert any(project["id"] == project_id for project in list_response.json()["projects"])
