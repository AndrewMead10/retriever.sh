from __future__ import annotations

from datetime import datetime
import json
import secrets
from typing import Any, Mapping, Optional, Sequence

import anyio
from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..config import settings
if settings.logfire_enabled:
    import logfire

from ..database import get_db
from ..database.models import User, UserSubscription, Plan, Project, ProjectDocument
from ..functions.accounts import decrement_vector_usage, ensure_vector_capacity, increment_usage
from ..functions.api_keys import verify_api_key
from ..functions.rate_limits import consume_rate_limit
from ..schemas.rag import DocumentIn, DocumentOut, QueryRequest, QueryResponse, QueryResult
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
