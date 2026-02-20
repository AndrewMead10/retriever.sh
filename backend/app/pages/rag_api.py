from __future__ import annotations

from datetime import datetime
import json
import secrets
from typing import Annotated
from typing import Any, Mapping, Optional, Sequence

import anyio
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Path, UploadFile, status
from sqlalchemy.orm import Session

from ..config import settings
if settings.logfire_enabled:
    import logfire

from ..database import get_db
from ..database.models import User, UserSubscription, Plan, Project, ProjectDocument, ProjectImage
from ..functions.accounts import decrement_vector_usage, ensure_vector_capacity, increment_usage
from ..functions.api_keys import verify_api_key
from ..functions.rate_limits import consume_rate_limit
from ..schemas.rag import (
    DocumentIn,
    DocumentOut,
    ImageOut,
    ImageQueryResponse,
    ImageQueryResult,
    ImageQueryTextRequest,
    QueryRequest,
    QueryResponse,
    QueryResult,
)
from ..services.image_storage import R2ImageStorageError, get_r2_image_storage
from ..services.search import normalise_fts_query
from ..services.vector_store import vector_store_registry

router = APIRouter(prefix="/rag", tags=["rag"])


def _load_project(session: Session, project_id: str) -> Project:
    project = (
        session.query(Project)
        .join(User, Project.user_id == User.id)
        .join(UserSubscription, UserSubscription.user_id == User.id)
        .join(Plan, UserSubscription.plan_id == Plan.id)
        .filter(Project.id == project_id, Project.active == True)
        .first()
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _verify_project_key(project: Project, api_key: str | None) -> None:
    if not api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Project API key required")
    if not verify_api_key(project.ingest_api_key_hash, api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid project API key")


def _get_plan(project: Project) -> Plan:
    subscription = project.user.subscription if project.user else None
    if subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription missing for project user")
    if subscription.plan is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Plan missing for project user")
    return subscription.plan


def _document_to_response(document: ProjectDocument) -> dict:
    return {
        "id": document.id,
        "content": document.content,
        "title": document.title,
        "metadata": document.metadata_ or {},
        "created_at": document.created_at,
    }


def _parse_metadata(value: Any) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _vespa_hit_to_response(hit: Mapping[str, Any]) -> dict:
    return {
        "id": hit.get("document_id"),
        "content": hit.get("content", ""),
        "title": hit.get("title", ""),
        "metadata": _parse_metadata(hit.get("metadata")),
        "created_at": hit.get("created_at"),
    }


def _parse_metadata_payload(payload: str | None) -> dict:
    if payload is None or not payload.strip():
        return {}
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="metadata must be valid JSON")
    if not isinstance(parsed, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="metadata must be a JSON object")
    return parsed


def _resolve_image_storage():
    try:
        return get_r2_image_storage()
    except R2ImageStorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def _validate_image_upload(file: UploadFile, image_bytes: bytes) -> str:
    if not image_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Image file is empty")
    if len(image_bytes) > settings.rag_image_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds upload size limit")

    content_type = (file.content_type or "").lower()
    allowed_types = {value.lower() for value in settings.rag_image_allowed_mime_types}
    if content_type not in allowed_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image content type: {content_type or 'unknown'}",
        )
    return content_type


def _image_to_response(image: ProjectImage) -> dict:
    storage = _resolve_image_storage()
    return {
        "id": image.id,
        "storage_key": image.storage_key,
        "content_type": image.content_type,
        "image_url": storage.resolve_url(image.storage_key),
        "metadata": image.metadata_ or {},
        "created_at": image.created_at,
    }


def _vespa_image_hit_to_response(hit: Mapping[str, Any]) -> dict:
    storage = _resolve_image_storage()
    storage_key = str(hit.get("storage_key") or "")
    return {
        "id": hit.get("image_id"),
        "storage_key": storage_key,
        "content_type": hit.get("content_type", "application/octet-stream"),
        "image_url": storage.resolve_url(storage_key) if storage_key else "",
        "metadata": _parse_metadata(hit.get("metadata")),
        "created_at": hit.get("created_at"),
    }


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_document(
    project_id: str = Path(...),
    payload: DocumentIn | None = None,
    db: Session = Depends(get_db),
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
):
    if payload is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing payload")

    project = _load_project(db, project_id)
    _verify_project_key(project, x_project_key)

    plan = _get_plan(project)
    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")

    ensure_vector_capacity(db, user=user, plan=plan, additional_vectors=1, project=project)
    consume_rate_limit(
        db,
        user_id=user.id,
        limit_type="ingest",
        error_detail="Ingestion rate limit exceeded. Upgrade to increase throughput.",
    )

    embedder = vector_store_registry.get_embedder(project)
    vector_store = vector_store_registry.get_vector_store(project)

    document = ProjectDocument(
        project_id=project.id,
        title=payload.title,
        content=payload.text,
        metadata_=payload.metadata or {},
        vespa_document_id=f"pending_{secrets.token_hex(8)}",
    )
    db.add(document)
    db.flush()

    document.vespa_document_id = f"{project.vector_store_path}_{document.id}"
    db.add(document)

    embedding = await anyio.to_thread.run_sync(
        lambda: embedder.embed_document(title=payload.title, text=payload.text)
    )
    await anyio.to_thread.run_sync(
        lambda: vector_store.upsert_document(document=document, embedding=embedding)
    )

    project.vector_count += 1
    project.last_ingest_at = datetime.utcnow()
    increment_usage(db, user=user, ingests=1, vectors=1)
    db.add_all([project, document])
    db.commit()
    db.refresh(document)

    return DocumentOut.model_validate(_document_to_response(document))


@router.post(
    "/projects/{project_id}/images",
    response_model=ImageOut,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_image(
    project_id: str = Path(...),
    image: UploadFile = File(...),
    metadata: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
):
    project = _load_project(db, project_id)
    _verify_project_key(project, x_project_key)

    plan = _get_plan(project)
    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")

    ensure_vector_capacity(db, user=user, plan=plan, additional_vectors=1, project=project)
    consume_rate_limit(
        db,
        user_id=user.id,
        limit_type="ingest",
        error_detail="Ingestion rate limit exceeded. Upgrade to increase throughput.",
    )

    image_bytes = await image.read()
    content_type = _validate_image_upload(image, image_bytes)
    parsed_metadata = _parse_metadata_payload(metadata)

    image_store = vector_store_registry.get_image_vector_store(project)
    image_embedder = vector_store_registry.get_image_embedder()
    object_storage = _resolve_image_storage()

    image_record = ProjectImage(
        project_id=project.id,
        vespa_document_id=f"pending_{secrets.token_hex(8)}",
        storage_key=f"pending_{secrets.token_hex(8)}",
        content_type=content_type,
        metadata_=parsed_metadata,
    )
    db.add(image_record)
    db.flush()

    image_record.vespa_document_id = f"{project.vector_store_path}_img_{image_record.id}"
    stored_image = await anyio.to_thread.run_sync(
        lambda: object_storage.upload_image(
            project_id=project.id,
            image_id=image_record.id,
            image_bytes=image_bytes,
            content_type=content_type,
            filename=image.filename,
        )
    )
    image_record.storage_key = stored_image.storage_key
    db.add(image_record)

    try:
        embedding = await anyio.to_thread.run_sync(
            lambda: image_embedder.embed_image(image_bytes=image_bytes)
        )
        await anyio.to_thread.run_sync(
            lambda: image_store.upsert_image(image=image_record, embedding=embedding)
        )
    except Exception:
        try:
            await anyio.to_thread.run_sync(
                lambda: object_storage.delete_image(storage_key=image_record.storage_key)
            )
        except Exception:
            pass
        raise

    project.vector_count += 1
    project.last_ingest_at = datetime.utcnow()
    increment_usage(db, user=user, ingests=1, vectors=1)
    db.add_all([project, image_record])
    db.commit()
    db.refresh(image_record)

    return ImageOut.model_validate(_image_to_response(image_record))


@router.delete(
    "/projects/{project_id}/vectors/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_vector(
    project_id: str = Path(...),
    document_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
):
    project = _load_project(db, project_id)
    _verify_project_key(project, x_project_key)

    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")

    document = (
        db.query(ProjectDocument)
        .filter(
            ProjectDocument.project_id == project.id,
            ProjectDocument.id == document_id,
            ProjectDocument.active == True,
        )
        .first()
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")

    vector_store = vector_store_registry.get_vector_store(project)
    await anyio.to_thread.run_sync(lambda: vector_store.delete_document(document))

    document.active = False
    db.add(document)

    project.vector_count = max(0, project.vector_count - 1)
    decrement_vector_usage(db, user=user, vectors=1)
    db.add(project)
    db.commit()
    return None


@router.delete(
    "/projects/{project_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_image(
    project_id: str = Path(...),
    image_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
):
    project = _load_project(db, project_id)
    _verify_project_key(project, x_project_key)

    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")

    image_record = (
        db.query(ProjectImage)
        .filter(
            ProjectImage.project_id == project.id,
            ProjectImage.id == image_id,
            ProjectImage.active == True,
        )
        .first()
    )
    if image_record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")

    image_store = vector_store_registry.get_image_vector_store(project)
    object_storage = _resolve_image_storage()
    await anyio.to_thread.run_sync(lambda: image_store.delete_image(image_record))
    await anyio.to_thread.run_sync(
        lambda: object_storage.delete_image(storage_key=image_record.storage_key)
    )

    image_record.active = False
    db.add(image_record)

    project.vector_count = max(0, project.vector_count - 1)
    decrement_vector_usage(db, user=user, vectors=1)
    db.add(project)
    db.commit()
    return None


@router.post(
    "/projects/{project_id}/query",
    response_model=QueryResponse,
)
async def query_project(
    project_id: str = Path(...),
    payload: QueryRequest | None = None,
    db: Session = Depends(get_db),
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
):
    if payload is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing payload")

    # Log query start if LogFire is enabled
    if settings.logfire_enabled:
        logfire.info(
            "RAG query started",
            project_id=project_id,
            query_length=len(payload.query) if payload and payload.query else 0,
            top_k=payload.top_k if payload else None,
            vector_k=payload.vector_k if payload else None,
        )

    project = _load_project(db, project_id)
    _verify_project_key(project, x_project_key)

    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")
    plan = _get_plan(project)

    consume_rate_limit(
        db,
        user_id=user.id,
        limit_type="query",
        error_detail="Query rate limit exceeded. Upgrade to increase throughput.",
    )

    embedder = vector_store_registry.get_embedder(project)
    vector_store = vector_store_registry.get_vector_store(project)

    top_k = payload.top_k or project.top_k_default
    vector_k = payload.vector_k or max(project.vector_search_k, top_k)

    embedding = await anyio.to_thread.run_sync(lambda: embedder.embed_query(query=payload.query))
    fts_query = normalise_fts_query(payload.query)

    rows = await anyio.to_thread.run_sync(
        lambda: vector_store.hybrid_search(
            embedding=embedding,
            vector_k=vector_k,
            top_k=top_k,
            weight_vector=project.hybrid_weight_vector,
            weight_text=project.hybrid_weight_text,
            fts_query=fts_query,
        )
    )

    increment_usage(db, user=user, queries=1)
    db.commit()

    results = [QueryResult.model_validate(_vespa_hit_to_response(row)) for row in rows]

    # Log query success if LogFire is enabled
    if settings.logfire_enabled:
        logfire.info(
            "RAG query completed successfully",
            project_id=project_id,
            result_count=len(results),
            user_id=user.id,
        )

    return QueryResponse(results=results)


@router.post(
    "/projects/{project_id}/images/query/text",
    response_model=ImageQueryResponse,
)
async def query_images_by_text(
    project_id: str = Path(...),
    payload: ImageQueryTextRequest | None = None,
    db: Session = Depends(get_db),
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
):
    if payload is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing payload")

    project = _load_project(db, project_id)
    _verify_project_key(project, x_project_key)

    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")

    consume_rate_limit(
        db,
        user_id=user.id,
        limit_type="query",
        error_detail="Query rate limit exceeded. Upgrade to increase throughput.",
    )

    image_embedder = vector_store_registry.get_image_embedder()
    image_store = vector_store_registry.get_image_vector_store(project)

    top_k = payload.top_k or project.top_k_default
    vector_k = payload.vector_k or max(project.vector_search_k, top_k)

    embedding = await anyio.to_thread.run_sync(
        lambda: image_embedder.embed_text(query=payload.query)
    )
    rows = await anyio.to_thread.run_sync(
        lambda: image_store.search(
            embedding=embedding,
            vector_k=vector_k,
            top_k=top_k,
        )
    )

    increment_usage(db, user=user, queries=1)
    db.commit()

    results = [ImageQueryResult.model_validate(_vespa_image_hit_to_response(row)) for row in rows]
    return ImageQueryResponse(results=results)


@router.post(
    "/projects/{project_id}/images/query/image",
    response_model=ImageQueryResponse,
)
async def query_images_by_image(
    project_id: str = Path(...),
    image: UploadFile = File(...),
    top_k: Annotated[int | None, Form()] = None,
    vector_k: Annotated[int | None, Form()] = None,
    db: Session = Depends(get_db),
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
):
    project = _load_project(db, project_id)
    _verify_project_key(project, x_project_key)

    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")

    consume_rate_limit(
        db,
        user_id=user.id,
        limit_type="query",
        error_detail="Query rate limit exceeded. Upgrade to increase throughput.",
    )

    image_bytes = await image.read()
    _validate_image_upload(image, image_bytes)

    resolved_top_k = top_k or project.top_k_default
    resolved_vector_k = vector_k or max(project.vector_search_k, resolved_top_k)
    if resolved_top_k < 1 or resolved_top_k > 50:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="top_k must be between 1 and 50")
    if resolved_vector_k < 1 or resolved_vector_k > 200:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="vector_k must be between 1 and 200")

    image_embedder = vector_store_registry.get_image_embedder()
    image_store = vector_store_registry.get_image_vector_store(project)

    embedding = await anyio.to_thread.run_sync(
        lambda: image_embedder.embed_image(image_bytes=image_bytes)
    )
    rows = await anyio.to_thread.run_sync(
        lambda: image_store.search(
            embedding=embedding,
            vector_k=resolved_vector_k,
            top_k=resolved_top_k,
        )
    )

    increment_usage(db, user=user, queries=1)
    db.commit()

    results = [ImageQueryResult.model_validate(_vespa_image_hit_to_response(row)) for row in rows]
    return ImageQueryResponse(results=results)
