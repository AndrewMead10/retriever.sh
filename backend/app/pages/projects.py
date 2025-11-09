from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..database.models import Project
from ..functions.accounts import (
    ensure_project_capacity,
    get_account,
    get_account_and_plan,
    get_per_project_vector_limit,
    get_project_limit,
    get_usage,
    get_vector_limit,
)
from ..functions.api_keys import generate_api_key, hash_api_key
from ..middleware.auth import get_current_user
from ..services.vector_store import vector_store_registry

router = APIRouter(prefix="/projects", tags=["projects"])


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "project"


class PlanInfo(BaseModel):
    slug: str
    name: str
    price_cents: int
    query_qps_limit: int
    ingest_qps_limit: int
    project_limit: Optional[int] = None
    vector_limit: Optional[int] = None
    per_project_vector_limit: Optional[int] = None


class UsageInfo(BaseModel):
    total_queries: int
    total_ingest_requests: int
    total_vectors: int
    project_count: int
    project_limit: Optional[int]
    vector_limit: Optional[int]


class ProjectSummary(BaseModel):
    id: int
    name: str
    description: Optional[str]
    slug: Optional[str]
    embedding_provider: str
    embedding_model: str
    embedding_model_repo: Optional[str]
    embedding_model_file: Optional[str]
    embedding_dim: int
    hybrid_weight_vector: float
    hybrid_weight_text: float
    top_k_default: int
    vector_search_k: int
    vector_count: int
    vector_store_path: str


class ProjectListResponse(BaseModel):
    projects: List[ProjectSummary]
    usage: UsageInfo
    plan: Optional[PlanInfo]
    needs_subscription: bool


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=512)
    embedding_provider: Optional[str] = Field(default="llama.cpp")
    embedding_model: Optional[str] = None
    embedding_model_repo: Optional[str] = None
    embedding_model_file: Optional[str] = None
    embedding_dim: Optional[int] = None
    hybrid_weight_vector: float = 0.5
    hybrid_weight_text: float = 0.5
    top_k_default: int = 5
    vector_search_k: int = 20


class ProjectCreateResponse(BaseModel):
    project: ProjectSummary
    ingest_api_key: str


def _vector_table_name(project_id: int) -> str:
    return f"rag_documents_proj_{project_id}"


@router.get("/onload", response_model=ProjectListResponse)
def projects_onload(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = get_account(db, user_id=current_user.id)
    subscription = account.subscription
    plan = subscription.plan if subscription else None
    usage = get_usage(db, account=account)
    projects = (
        db.query(Project)
        .filter(Project.account_id == account.id, Project.active == True)
        .order_by(Project.created_at.desc())
        .all()
    )

    needs_subscription = plan is None
    vector_limit = get_vector_limit(db, account=account, plan=plan) if plan else None
    project_limit = get_project_limit(plan) if plan else None

    return ProjectListResponse(
        projects=[
            ProjectSummary(
                id=project.id,
                name=project.name,
                description=project.description,
                slug=project.slug,
                embedding_provider=project.embedding_provider,
                embedding_model=project.embedding_model,
                embedding_model_repo=project.embedding_model_repo,
                embedding_model_file=project.embedding_model_file,
                embedding_dim=project.embedding_dim,
                hybrid_weight_vector=project.hybrid_weight_vector,
                hybrid_weight_text=project.hybrid_weight_text,
                top_k_default=project.top_k_default,
                vector_search_k=project.vector_search_k,
                vector_count=project.vector_count,
                vector_store_path=project.vector_store_path,
            )
            for project in projects
        ],
        usage=UsageInfo(
            total_queries=usage.total_queries,
            total_ingest_requests=usage.total_ingest_requests,
            total_vectors=usage.total_vectors,
            project_count=len(projects),
            project_limit=project_limit,
            vector_limit=vector_limit,
        ),
        plan=PlanInfo(
            slug=plan.slug,
            name=plan.name,
            price_cents=plan.price_cents,
            query_qps_limit=plan.query_qps_limit,
            ingest_qps_limit=plan.ingest_qps_limit,
            project_limit=project_limit,
            vector_limit=vector_limit,
            per_project_vector_limit=get_per_project_vector_limit(plan),
        ) if plan else None,
        needs_subscription=needs_subscription,
    )


@router.post("/onsubmit", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account, plan = get_account_and_plan(db, user_id=current_user.id)

    ensure_project_capacity(db, account=account, plan=plan)

    name = payload.name.strip()
    slug = _slugify(name)

    existing_slug = (
        db.query(Project)
        .filter(Project.account_id == account.id, Project.slug == slug, Project.active == True)
        .first()
    )
    if existing_slug:
        slug = f"{slug}-{existing_slug.id + 1}"

    embedding_provider = payload.embedding_provider or "llama.cpp"
    embedding_model = payload.embedding_model or settings.rag_model_filename
    embedding_model_repo = payload.embedding_model_repo or settings.rag_model_repo
    embedding_model_file = payload.embedding_model_file or settings.rag_model_filename
    embedding_dim = payload.embedding_dim or settings.rag_embed_dim

    ingest_key_plain = generate_api_key(prefix="proj")
    ingest_key_hash = hash_api_key(ingest_key_plain)

    project = Project(
        account_id=account.id,
        name=name,
        description=payload.description,
        slug=slug,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_model_repo=embedding_model_repo,
        embedding_model_file=embedding_model_file,
        embedding_dim=embedding_dim,
        hybrid_weight_vector=payload.hybrid_weight_vector,
        hybrid_weight_text=payload.hybrid_weight_text,
        top_k_default=payload.top_k_default,
        vector_search_k=payload.vector_search_k,
        vector_store_path=f"pending_{slug}",
        ingest_api_key_hash=ingest_key_hash,
    )
    db.add(project)
    db.flush()

    project.vector_store_path = _vector_table_name(project.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Ensure the vector store exists and is initialised.
    vector_store_registry.get_database(project)

    project_summary = ProjectSummary(
        id=project.id,
        name=project.name,
        description=project.description,
        slug=project.slug,
        embedding_provider=project.embedding_provider,
        embedding_model=project.embedding_model,
        embedding_model_repo=project.embedding_model_repo,
        embedding_model_file=project.embedding_model_file,
        embedding_dim=project.embedding_dim,
        hybrid_weight_vector=project.hybrid_weight_vector,
        hybrid_weight_text=project.hybrid_weight_text,
        top_k_default=project.top_k_default,
        vector_search_k=project.vector_search_k,
        vector_count=project.vector_count,
        vector_store_path=project.vector_store_path,
    )

    return ProjectCreateResponse(project=project_summary, ingest_api_key=ingest_key_plain)


class ProjectDeleteRequest(BaseModel):
    project_id: int


@router.post("/delete", status_code=status.HTTP_200_OK)
def delete_project(
    payload: ProjectDeleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = get_account(db, user_id=current_user.id)

    # Find the project and verify it belongs to the user's account
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.account_id == account.id, Project.active == True)
        .first()
    )

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Mark the project as inactive
    project.active = False
    db.add(project)
    db.commit()

    # Mark all vectors in the project's table as inactive
    try:
        vector_store = vector_store_registry.get_database(project)
        if vector_store.is_ready():
            from sqlalchemy import text as sql_text
            session = db
            session.execute(
                sql_text(f"UPDATE {project.vector_store_path} SET active = 0 WHERE project_id = :project_id"),
                {"project_id": project.id}
            )
            session.commit()
    except Exception as e:
        # Log the error but don't fail the delete operation
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Failed to mark vectors as inactive for project {project.id}: {e}")

    return {"detail": "Project deleted successfully"}
