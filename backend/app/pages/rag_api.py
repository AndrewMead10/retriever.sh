from __future__ import annotations

import json
import secrets
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import anyio
from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..config import settings
if settings.logfire_enabled:
    import logfire
else:
    logfire = None

from ..database import get_db
from ..database.models import User, UserSubscription, Plan, Project, ProjectDocument
from ..functions.accounts import decrement_vector_usage, ensure_vector_capacity, increment_usage
from ..functions.api_keys import authenticate_project_api_key
from ..functions.rate_limits import consume_rate_limit
from ..schemas.rag import (
    ContentBlock,
    ItemIn,
    ItemOut,
    QueryRequest,
    QueryResponse,
    QueryResult,
)
from ..services.search import normalise_fts_query
from ..services.text_embeddings import EmbeddingProviderError
from ..services.vector_store import vector_store_registry

router = APIRouter(prefix="/rag", tags=["rag"])

CONTENT_BLOCKS_METADATA_KEY = "__retriever_content"
EXTERNAL_ID_METADATA_KEY = "__retriever_external_id"
ITEM_DATE_METADATA_KEY = "__retriever_date"


def _logfire_span(message_template: str, **attributes: Any):
    if settings.logfire_enabled and logfire is not None:
        return logfire.span(message_template, **attributes)
    return nullcontext()


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


def _get_plan(project: Project) -> Plan:
    subscription = project.user.subscription if project.user else None
    if subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription missing for project user")
    if subscription.plan is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Plan missing for project user")
    return subscription.plan


def _item_to_response(document: ProjectDocument) -> dict:
    metadata = dict(document.metadata_ or {})
    return {
        "id": document.id,
        "title": document.title,
        "content": _content_blocks_from_metadata(metadata, fallback=document.content),
        "metadata": _public_metadata(metadata),
        "external_id": metadata.get(EXTERNAL_ID_METADATA_KEY),
        "date": metadata.get(ITEM_DATE_METADATA_KEY),
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


def _public_metadata(metadata: Mapping[str, Any]) -> dict:
    return {
        key: value
        for key, value in metadata.items()
        if key not in {CONTENT_BLOCKS_METADATA_KEY, EXTERNAL_ID_METADATA_KEY, ITEM_DATE_METADATA_KEY}
    }


def _content_blocks_from_metadata(metadata: Mapping[str, Any], *, fallback: str) -> list[dict]:
    blocks = metadata.get(CONTENT_BLOCKS_METADATA_KEY)
    if isinstance(blocks, list) and blocks:
        return [block for block in blocks if isinstance(block, dict)]
    return [{"type": "text", "text": fallback}]


def _metadata_for_item(payload: ItemIn) -> dict:
    metadata = dict(payload.metadata or {})
    metadata[CONTENT_BLOCKS_METADATA_KEY] = _dump_content_blocks(payload.content)
    if payload.external_id is not None:
        metadata[EXTERNAL_ID_METADATA_KEY] = payload.external_id
    if payload.date is not None:
        metadata[ITEM_DATE_METADATA_KEY] = _datetime_to_utc_iso(payload.date)
    return metadata


def _dump_content_blocks(blocks: list[ContentBlock]) -> list[dict]:
    return [block.model_dump() for block in blocks]


def _datetime_to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _content_text_projection(title: str, blocks: list[ContentBlock]) -> str:
    parts: list[str] = []
    for block in blocks:
        data = block.model_dump()
        block_type = data["type"]
        if block_type == "text":
            value = data["text"].strip()
        elif block_type.endswith("_url"):
            value = f"{block_type.removesuffix('_url')}: {data['url'].strip()}"
        else:
            media_type = data.get("media_type", "base64")
            value = f"{block_type.removesuffix('_base64')}: {media_type}"
        if value:
            parts.append(value)

    projection = "\n\n".join(parts).strip()
    if projection:
        return projection
    return title.strip()


def _text_blocks_projection(blocks: list[ContentBlock]) -> str:
    values = []
    for block in blocks:
        data = block.model_dump()
        if data["type"] == "text":
            value = data["text"].strip()
            if value:
                values.append(value)
    return "\n\n".join(values)


def _vespa_hit_to_response(hit: Mapping[str, Any]) -> dict:
    metadata = _parse_metadata(hit.get("metadata"))
    return {
        "id": hit.get("document_id"),
        "title": hit.get("title", ""),
        "content": _content_blocks_from_metadata(metadata, fallback=str(hit.get("content", ""))),
        "metadata": _public_metadata(metadata),
        "external_id": metadata.get(EXTERNAL_ID_METADATA_KEY),
        "date": metadata.get(ITEM_DATE_METADATA_KEY),
        "created_at": hit.get("created_at"),
        "score": hit.get("_vespa_relevance"),
    }


@router.post(
    "/projects/{project_id}/items",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_item(
    project_id: str = Path(...),
    payload: ItemIn | None = None,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    if payload is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing payload")

    project = _load_project(db, project_id)
    authenticate_project_api_key(db, project=project, authorization=authorization)

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
        content=_content_text_projection(payload.title, payload.content),
        metadata_=_metadata_for_item(payload),
        vespa_document_id=f"pending_{secrets.token_hex(8)}",
    )
    db.add(document)
    db.flush()

    document.vespa_document_id = f"{project.vector_store_path}_{document.id}"
    db.add(document)

    try:
        embedding = await anyio.to_thread.run_sync(
            lambda: embedder.embed_item(
                title=payload.title,
                content=_dump_content_blocks(payload.content),
            ),
            cancellable=True,
        )
    except EmbeddingProviderError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    await anyio.to_thread.run_sync(
        lambda: vector_store.upsert_document(document=document, embedding=embedding)
    )

    project.vector_count += 1
    project.last_ingest_at = datetime.utcnow()
    increment_usage(db, user=user, ingests=1, vectors=1)
    db.add_all([project, document])
    db.commit()
    db.refresh(document)

    return ItemOut.model_validate(_item_to_response(document))


@router.delete(
    "/projects/{project_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_item(
    project_id: str = Path(...),
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    project = _load_project(db, project_id)
    authenticate_project_api_key(db, project=project, authorization=authorization)

    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")

    document = (
        db.query(ProjectDocument)
        .filter(
            ProjectDocument.project_id == project.id,
            ProjectDocument.id == item_id,
            ProjectDocument.active == True,
        )
        .first()
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item not found")

    vector_store = vector_store_registry.get_vector_store(project)
    await anyio.to_thread.run_sync(lambda: vector_store.delete_document(document))

    document.active = False
    db.add(document)

    project.vector_count = max(0, project.vector_count - 1)
    decrement_vector_usage(db, user=user, vectors=1)
    db.add(project)
    db.commit()
    return None


@router.get("/projects/{project_id}/auth/check")
def check_project_api_key(
    project_id: str = Path(...),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    project = _load_project(db, project_id)
    api_key = authenticate_project_api_key(db, project=project, authorization=authorization)
    db.commit()
    return {
        "detail": "Project API key is valid",
        "project_id": project.id,
        "project_name": project.name,
        "api_key_prefix": api_key.prefix,
    }


@router.post(
    "/projects/{project_id}/query",
    response_model=QueryResponse,
)
async def query_project(
    project_id: str = Path(...),
    payload: QueryRequest | None = None,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    if payload is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing payload")

    # Log query start if LogFire is enabled
    if settings.logfire_enabled:
        logfire.info(
            "RAG query started",
            project_id=project_id,
            input_blocks=len(payload.input) if payload else 0,
            top_k=payload.top_k if payload else None,
            vector_k=payload.vector_k if payload else None,
        )

    project = _load_project(db, project_id)
    authenticate_project_api_key(db, project=project, authorization=authorization)

    user = project.user
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")
    user_id = user.id
    top_k = payload.top_k or project.top_k_default
    vector_k = payload.vector_k or max(project.vector_search_k, top_k)
    weight_vector = project.hybrid_weight_vector
    weight_text = project.hybrid_weight_text

    consume_rate_limit(
        db,
        user_id=user_id,
        limit_type="query",
        error_detail="Query rate limit exceeded. Upgrade to increase throughput.",
    )

    embedder = vector_store_registry.get_embedder(project)
    vector_store = vector_store_registry.get_vector_store(project)
    db.commit()

    with _logfire_span(
        "RAG query pipeline",
        project_id=project_id,
        input_blocks=len(payload.input),
        top_k=top_k,
        vector_k=vector_k,
    ):
        with _logfire_span("Generate query embedding", project_id=project_id):
            try:
                embedding = await anyio.to_thread.run_sync(
                    lambda: embedder.embed_query(content=_dump_content_blocks(payload.input)),
                    cancellable=True,
                )
            except EmbeddingProviderError as exc:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        with _logfire_span("Normalise full-text search query", project_id=project_id):
            query_text = _text_blocks_projection(payload.input)
            fts_query = normalise_fts_query(query_text)

        with _logfire_span("Execute hybrid search", project_id=project_id):
            rows = await anyio.to_thread.run_sync(
                lambda: vector_store.hybrid_search(
                    embedding=embedding,
                    vector_k=vector_k,
                    top_k=top_k,
                    weight_vector=weight_vector,
                    weight_text=weight_text,
                    fts_query=fts_query,
                    date_from=payload.date_from,
                    date_to=payload.date_to,
                )
            )

    with _logfire_span(
        "Persist query usage",
        project_id=project_id,
        user_id=user_id,
        result_count=len(rows),
    ):
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User missing for project")
        increment_usage(db, user=user, queries=1)
        db.commit()

    with _logfire_span("Map query results", project_id=project_id, result_count=len(rows)):
        results = [QueryResult.model_validate(_vespa_hit_to_response(row)) for row in rows]

    # Log query success if LogFire is enabled
    if settings.logfire_enabled and logfire is not None:
        logfire.info(
            "RAG query completed successfully",
            project_id=project_id,
            result_count=len(results),
            user_id=user_id,
        )

    return QueryResponse(results=results)
