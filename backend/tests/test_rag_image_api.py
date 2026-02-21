from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.database import models  # noqa: F401
from app.database.models import (
    Base,
    Plan,
    Project,
    ProjectImage,
    RateLimitBucket,
    User,
    UserSubscription,
    UserUsage,
)
from app.functions.api_keys import generate_api_key, hash_api_key
from app.main import app
from app.pages import rag_api
from app.services.image_storage import StoredImage


_SAMPLE_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x89\x1f\xa0"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


class _StubImageEmbedder:
    def __init__(self, *, fail_on_image: bool = False) -> None:
        self.fail_on_image = fail_on_image
        self.embed_image_calls = 0
        self.embed_text_calls = 0

    def embed_image(self, *, image_bytes: bytes):
        self.embed_image_calls += 1
        if self.fail_on_image:
            raise ValueError("unsupported image tensor shape")
        return [0.1, -0.2, 0.3, -0.4]

    def embed_text(self, *, query: str):
        self.embed_text_calls += 1
        return [0.5, -0.25, 0.125, -0.0625]


class _StubImageStore:
    def __init__(self, *, hits: list[dict[str, Any]] | None = None) -> None:
        self.hits = hits or []
        self.upserts: list[tuple[int, int]] = []
        self.deletes: list[int] = []
        self.last_search: tuple[int, int] | None = None

    def upsert_image(self, *, image: ProjectImage, embedding):
        self.upserts.append((image.id, len(embedding)))

    def search(self, *, embedding, vector_k: int, top_k: int):
        self.last_search = (vector_k, top_k)
        return list(self.hits)

    def delete_image(self, image: ProjectImage):
        self.deletes.append(image.id)
        return True


class _StubImageStorage:
    def __init__(self, *, fail_on_delete: bool = False) -> None:
        self.fail_on_delete = fail_on_delete
        self.uploaded: list[str] = []
        self.deleted: list[str] = []

    def upload_image(
        self,
        *,
        project_id: str,
        image_id: int,
        image_bytes: bytes,
        content_type: str,
        filename: str | None,
    ) -> StoredImage:
        key = f"projects/{project_id}/images/{image_id}/uploaded.png"
        self.uploaded.append(key)
        return StoredImage(storage_key=key, url=f"https://cdn.example/{key}")

    def delete_image(self, *, storage_key: str):
        self.deleted.append(storage_key)
        if self.fail_on_delete:
            raise RuntimeError("r2 temporarily unavailable")
        return True

    def resolve_url(self, storage_key: str) -> str:
        return f"https://cdn.example/{storage_key}"


@pytest.fixture
def engine():
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="test_rag_image_api_")
    os.close(db_fd)
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


@pytest.fixture
def session(engine) -> Session:
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_client(session: Session, monkeypatch: pytest.MonkeyPatch):
    from app.config import settings
    from app.database import get_db

    monkeypatch.setattr(settings, "logfire_enabled", False)

    def override_get_db():
        yield session

    startup_handlers = list(app.router.on_startup)
    shutdown_handlers = list(app.router.on_shutdown)
    app.router.on_startup = []
    app.router.on_shutdown = []
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        app.router.on_startup = startup_handlers
        app.router.on_shutdown = shutdown_handlers


@pytest.fixture
def seeded_project(session: Session):
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

    user = User(
        email="img-test@example.com",
        hashed_password="hashed",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(user)
    session.flush()

    session.add_all(
        [
            UserSubscription(
                user_id=user.id,
                plan_id=plan.id,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            UserUsage(
                user_id=user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            RateLimitBucket(
                user_id=user.id,
                limit_type="query",
                tokens=plan.query_qps_limit,
                last_refill=datetime.utcnow(),
                max_tokens=plan.query_qps_limit,
            ),
            RateLimitBucket(
                user_id=user.id,
                limit_type="ingest",
                tokens=plan.ingest_qps_limit,
                last_refill=datetime.utcnow(),
                max_tokens=plan.ingest_qps_limit,
            ),
        ]
    )
    session.flush()

    api_key = generate_api_key(prefix="proj")
    project = Project(
        user_id=user.id,
        name="Image Test Project",
        description="Image API tests",
        slug="image-test-project",
        embedding_provider="llama.cpp",
        embedding_model="nomic-embed-text-v1.5.Q8_0.gguf",
        embedding_model_repo="nomic-ai/nomic-embed-text-v1.5-GGUF",
        embedding_model_file="nomic-embed-text-v1.5.Q8_0.gguf",
        embedding_dim=256,
        hybrid_weight_vector=0.7,
        hybrid_weight_text=0.3,
        top_k_default=5,
        vector_search_k=20,
        vector_store_path="img_test_project",
        vector_count=0,
        ingest_api_key_hash=hash_api_key(api_key),
        active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    return {"project": project, "api_key": api_key, "user": user}


def test_ingest_image_success(test_client: TestClient, seeded_project, session: Session, monkeypatch):
    project = seeded_project["project"]
    storage = _StubImageStorage()
    store = _StubImageStore()
    embedder = _StubImageEmbedder()

    monkeypatch.setattr(rag_api, "_resolve_image_storage", lambda: storage)
    monkeypatch.setattr(rag_api, "_resolve_image_embedder", lambda: embedder)
    monkeypatch.setattr(rag_api.vector_store_registry, "get_image_vector_store", lambda _: store)

    response = test_client.post(
        f"/api/rag/projects/{project.id}/images",
        headers={"X-Project-Key": seeded_project["api_key"]},
        files={"image": ("tiny.png", _SAMPLE_PNG_BYTES, "image/png")},
        data={"metadata": json.dumps({"source": "unit-test"})},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["content_type"] == "image/png"
    assert payload["metadata"] == {"source": "unit-test"}
    assert payload["image_url"].startswith("https://cdn.example/")
    assert len(store.upserts) == 1
    assert len(storage.uploaded) == 1

    session.refresh(project)
    assert project.vector_count == 1


def test_ingest_image_returns_400_on_embed_validation_error(
    test_client: TestClient,
    seeded_project,
    monkeypatch,
):
    project = seeded_project["project"]
    storage = _StubImageStorage()
    store = _StubImageStore()
    embedder = _StubImageEmbedder(fail_on_image=True)

    monkeypatch.setattr(rag_api, "_resolve_image_storage", lambda: storage)
    monkeypatch.setattr(rag_api, "_resolve_image_embedder", lambda: embedder)
    monkeypatch.setattr(rag_api.vector_store_registry, "get_image_vector_store", lambda _: store)

    response = test_client.post(
        f"/api/rag/projects/{project.id}/images",
        headers={"X-Project-Key": seeded_project["api_key"]},
        files={"image": ("tiny.png", _SAMPLE_PNG_BYTES, "image/png")},
    )

    assert response.status_code == 400
    assert "Invalid image payload" in response.json()["detail"]
    assert len(storage.uploaded) == 1
    assert len(storage.deleted) == 1
    assert store.upserts == []


def test_query_images_by_text_and_image(test_client: TestClient, seeded_project, monkeypatch):
    project = seeded_project["project"]
    storage = _StubImageStorage()
    embedder = _StubImageEmbedder()
    store = _StubImageStore(
        hits=[
            {
                "image_id": 1,
                "storage_key": "projects/p/images/1/uploaded.png",
                "content_type": "image/png",
                "metadata": json.dumps({"label": "cat"}),
                "created_at": datetime.utcnow().isoformat(),
                "_vespa_relevance": 0.42,
            }
        ]
    )

    monkeypatch.setattr(rag_api, "_resolve_image_storage", lambda: storage)
    monkeypatch.setattr(rag_api, "_resolve_image_embedder", lambda: embedder)
    monkeypatch.setattr(rag_api.vector_store_registry, "get_image_vector_store", lambda _: store)

    text_response = test_client.post(
        f"/api/rag/projects/{project.id}/images/query/text",
        headers={"X-Project-Key": seeded_project["api_key"]},
        json={"query": "cat photo", "top_k": 2, "vector_k": 4},
    )
    assert text_response.status_code == 200, text_response.text
    text_results = text_response.json()["results"]
    assert len(text_results) == 1
    assert text_results[0]["metadata"] == {"label": "cat"}
    assert text_results[0]["score"] == pytest.approx(0.42)
    assert embedder.embed_text_calls == 1
    assert store.last_search == (4, 2)

    image_response = test_client.post(
        f"/api/rag/projects/{project.id}/images/query/image",
        headers={"X-Project-Key": seeded_project["api_key"]},
        files={"image": ("tiny.png", _SAMPLE_PNG_BYTES, "image/png")},
        data={"top_k": "2", "vector_k": "4"},
    )
    assert image_response.status_code == 200, image_response.text
    image_results = image_response.json()["results"]
    assert len(image_results) == 1
    assert image_results[0]["image_url"].startswith("https://cdn.example/")
    assert image_results[0]["score"] == pytest.approx(0.42)
    assert embedder.embed_image_calls == 1


def test_delete_image_marks_inactive_when_r2_delete_fails(
    test_client: TestClient,
    seeded_project,
    session: Session,
    monkeypatch,
):
    project = seeded_project["project"]
    storage = _StubImageStorage(fail_on_delete=True)
    store = _StubImageStore()

    image = ProjectImage(
        project_id=project.id,
        vespa_document_id=f"{project.vector_store_path}_img_1",
        storage_key=f"projects/{project.id}/images/1/uploaded.png",
        content_type="image/png",
        metadata_={},
        active=True,
    )
    project.vector_count = 1
    session.add_all([project, image])
    session.commit()
    session.refresh(image)

    monkeypatch.setattr(rag_api, "_resolve_image_storage", lambda: storage)
    monkeypatch.setattr(rag_api.vector_store_registry, "get_image_vector_store", lambda _: store)

    response = test_client.delete(
        f"/api/rag/projects/{project.id}/images/{image.id}",
        headers={"X-Project-Key": seeded_project["api_key"]},
    )

    assert response.status_code == 204, response.text
    session.refresh(image)
    session.refresh(project)
    assert image.active is False
    assert project.vector_count == 0
    assert store.deletes == [image.id]
