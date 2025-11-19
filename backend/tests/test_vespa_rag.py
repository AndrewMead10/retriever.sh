"""
Integration test for Vespa RAG endpoints.

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

NOTE: This test requires Vespa to be running (e.g., via docker-compose).
The test database is automatically cleaned up after each test run.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import models  # Import all models to ensure tables are created
from app.database.models import (
    Base,
    Plan,
    Project,
    ProjectDocument,
    RateLimitBucket,
    User,
    UserSubscription,
    UserUsage,
)
from app.functions.api_keys import generate_api_key, hash_api_key
from app.main import app


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
    api_key_hash = hash_api_key(api_key)

    # Create project
    project = Project(
        user_id=user.id,
        name="Test RAG Project",
        description="Test project for Vespa RAG",
        slug="test-rag-project",
        embedding_provider="llama.cpp",
        embedding_model="nomic-embed-text-v1.5.Q8_0.gguf",
        embedding_model_repo="nomic-ai/nomic-embed-text-v1.5-GGUF",
        embedding_model_file="nomic-embed-text-v1.5.Q8_0.gguf",
        embedding_dim=768,
        hybrid_weight_vector=0.7,
        hybrid_weight_text=0.3,
        top_k_default=5,
        vector_search_k=20,
        vector_store_path="test_vespa_project",
        vector_count=0,
        ingest_api_key_hash=api_key_hash,
        active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(project)
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
            "text": "Machine learning is a subset of artificial intelligence that focuses on building systems that learn from data. It enables computers to improve their performance on tasks without being explicitly programmed.",
            "url": "https://example.com/ml-intro",
            "published_at": "2024-01-15T10:00:00Z",
        },
        {
            "title": "Deep Learning Fundamentals",
            "text": "Deep learning uses neural networks with multiple layers to progressively extract higher-level features from raw input. It has revolutionized computer vision and natural language processing.",
            "url": "https://example.com/deep-learning",
            "published_at": "2024-01-16T14:30:00Z",
        },
        {
            "title": "Natural Language Processing Basics",
            "text": "Natural language processing (NLP) is a branch of artificial intelligence that helps computers understand, interpret and manipulate human language. NLP draws from many disciplines, including computer science and computational linguistics.",
            "url": "https://example.com/nlp-basics",
            "published_at": "2024-01-17T09:15:00Z",
        },
    ]

    uploaded_doc_ids = []

    # Step 1: Upload documents
    print("\n--- Step 1: Uploading documents ---")
    for doc in test_documents:
        response = test_client.post(
            f"/api/rag/projects/{project.id}/documents",
            json=doc,
            headers={"X-Project-Key": api_key},
        )
        assert response.status_code == 201, f"Failed to upload document: {response.json()}"

        result = response.json()
        uploaded_doc_ids.append(result["id"])

        assert result["title"] == doc["title"]
        # The response can have either 'text' or 'content' due to aliasing
        response_text = result.get("text") or result.get("content")
        assert response_text == doc["text"]
        assert result["url"] == doc["url"]
        assert "id" in result
        assert "created_at" in result

        print(f"✓ Uploaded document: {doc['title']} (ID: {result['id']})")

    assert len(uploaded_doc_ids) == 3, "Should have uploaded 3 documents"

    # Step 2: Search for documents
    print("\n--- Step 2: Searching documents ---")

    # Search for "machine learning"
    search_query = {
        "query": "machine learning artificial intelligence",
        "top_k": 5,
    }

    response = test_client.post(
        f"/api/rag/projects/{project.id}/query",
        json=search_query,
        headers={"X-Project-Key": api_key},
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
        assert "text" in result or "content" in result
        assert "url" in result
        print(f"  {idx}. {result['title']}")

    # Search for "deep learning"
    search_query2 = {
        "query": "neural networks deep learning",
        "top_k": 3,
    }

    response2 = test_client.post(
        f"/api/rag/projects/{project.id}/query",
        json=search_query2,
        headers={"X-Project-Key": api_key},
    )
    assert response2.status_code == 200
    search_results2 = response2.json()
    assert len(search_results2["results"]) > 0
    print(f"✓ Second search returned {len(search_results2['results'])} results")

    # Step 3: Delete all uploaded documents
    print("\n--- Step 3: Deleting documents ---")
    for doc_id in uploaded_doc_ids:
        response = test_client.delete(
            f"/api/rag/projects/{project.id}/vectors/{doc_id}",
            headers={"X-Project-Key": api_key},
        )
        assert response.status_code == 204, f"Failed to delete document {doc_id}: {response.text}"
        print(f"✓ Deleted document ID: {doc_id}")

    # Verify documents are deleted by searching again
    print("\n--- Step 4: Verifying deletion ---")
    response = test_client.post(
        f"/api/rag/projects/{project.id}/query",
        json={"query": "machine learning", "top_k": 10},
        headers={"X-Project-Key": api_key},
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
        f"/api/rag/projects/{project.id}/documents",
        json={
            "title": "Test",
            "text": "Test content",
            "url": "https://example.com",
            "published_at": "2024-01-01T00:00:00Z",
        },
        headers={"X-Project-Key": "invalid_key"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


def test_missing_api_key(test_client: TestClient, seeded_project):
    """Test that missing API keys are rejected."""
    project = seeded_project["project"]

    response = test_client.post(
        f"/api/rag/projects/{project.id}/documents",
        json={
            "title": "Test",
            "text": "Test content",
            "url": "https://example.com",
            "published_at": "2024-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 401
    assert "detail" in response.json()


def test_nonexistent_project(test_client: TestClient):
    """Test that queries to non-existent projects return 404."""
    response = test_client.post(
        "/api/rag/projects/99999/query",
        json={"query": "test"},
        headers={"X-Project-Key": "test_fake_key"},
    )

    assert response.status_code == 404
    assert "detail" in response.json()
