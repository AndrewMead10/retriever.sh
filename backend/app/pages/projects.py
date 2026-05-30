from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..database.models import Project, ProjectDocument
from ..functions.accounts import (
    ensure_project_capacity,
    get_user,
    get_user_and_plan,
    get_per_project_vector_limit,
    get_project_limit,
    get_usage,
)
from ..functions.api_keys import (
    authenticate_management_api_key,
    create_project_api_key,
    expires_at_from_days,
    record_api_key_audit_event,
)
from ..middleware.auth import get_current_user
from ..services.vector_store import vector_store_registry

router = APIRouter(prefix="/projects", tags=["projects"])


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "project"


def _build_unique_slug(db: Session, user_id: int, base_slug: str) -> str:
    matching_slugs = (
        db.query(Project.slug)
        .filter(
            Project.user_id == user_id,
            Project.active == True,
            Project.slug.isnot(None),
            or_(Project.slug == base_slug, Project.slug.like(f"{base_slug}-%")),
        )
        .all()
    )
    used = {slug for (slug,) in matching_slugs if slug}
    if base_slug not in used:
        return base_slug

    suffix = 2
    while f"{base_slug}-{suffix}" in used:
        suffix += 1
    return f"{base_slug}-{suffix}"


class PlanInfo(BaseModel):
    slug: str
    name: str
    price_cents: int
    query_qps_limit: int
    ingest_qps_limit: int
    project_limit: Optional[int] = None
    vector_limit: Optional[int] = None


class UsageInfo(BaseModel):
    total_queries: int
    total_ingest_requests: int
    total_vectors: int
    project_count: int
    project_limit: Optional[int]
    vector_limit: Optional[int]


class ProjectSummary(BaseModel):
    id: str
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
    embedding_provider: Optional[str] = Field(default="remote-http")
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
    api_key: str
    api_key_prefix: str
    authorization_header: str


class ProjectRotateKeyRequest(BaseModel):
    project_id: str
    name: Optional[str] = None
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3660)


class ProjectApiKeyResponse(BaseModel):
    project_id: str
    api_key: str
    api_key_prefix: str
    authorization_header: str


class ProjectManagementCreateRequest(ProjectCreateRequest):
    api_key_name: Optional[str] = Field(default="Agent project key", max_length=120)
    api_key_expires_in_days: Optional[int] = Field(default=None, ge=1, le=3660)


class ProjectManagementCreateResponse(ProjectCreateResponse):
    pass


class ProjectManagementListResponse(BaseModel):
    projects: List[ProjectSummary]


class ProjectCreateApiKeyRequest(BaseModel):
    name: str = Field(default="Agent project key", min_length=1, max_length=120)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3660)


def _vector_table_name(project_id: str) -> str:
    return f"vespa_proj_{project_id}"


def _project_summary(project: Project) -> ProjectSummary:
    return ProjectSummary(
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


def _create_project(
    db: Session,
    *,
    user,
    payload: ProjectCreateRequest,
    api_key_name: str = "Default API key",
    api_key_expires_at: datetime | None = None,
) -> tuple[Project, str, str]:
    name = payload.name.strip()
    slug = _build_unique_slug(db, user.id, _slugify(name))

    embedding_provider = payload.embedding_provider or "remote-http"
    embedding_model = payload.embedding_model or settings.rag_embedding_model
    embedding_model_repo = payload.embedding_model_repo
    embedding_model_file = payload.embedding_model_file
    embedding_dim = payload.embedding_dim or settings.rag_embed_dim

    project = Project(
        user_id=user.id,
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
    )
    db.add(project)
    db.flush()

    project.vector_store_path = _vector_table_name(project.id)
    db.add(project)
    key, plain_key = create_project_api_key(
        db,
        project=project,
        name=api_key_name,
        expires_at=api_key_expires_at,
    )
    db.commit()
    db.refresh(project)
    return project, plain_key, key.prefix


@router.get("/onload", response_model=ProjectListResponse)
def projects_onload(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = get_user(db, user_id=current_user.id)
    subscription = user.subscription
    plan = subscription.plan if subscription else None
    usage = get_usage(db, user=user)
    projects = (
        db.query(Project)
        .filter(Project.user_id == user.id, Project.active == True)
        .order_by(Project.created_at.desc())
        .all()
    )

    needs_subscription = plan is None
    vector_limit = get_per_project_vector_limit(plan) if plan else None
    project_limit = get_project_limit(plan) if plan else None

    return ProjectListResponse(
        projects=[_project_summary(project) for project in projects],
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
        ) if plan else None,
        needs_subscription=needs_subscription,
    )


@router.post("/onsubmit", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user, plan = get_user_and_plan(db, user_id=current_user.id)

    ensure_project_capacity(db, user=user, plan=plan)

    project, api_key, api_key_prefix = _create_project(
        db,
        user=user,
        payload=payload,
        api_key_name="Dashboard project key",
    )

    return ProjectCreateResponse(
        project=_project_summary(project),
        api_key=api_key,
        api_key_prefix=api_key_prefix,
        authorization_header=f"Bearer {api_key}",
    )


@router.post("/rotate-api-key", response_model=ProjectApiKeyResponse)
def rotate_project_api_key(
    payload: ProjectRotateKeyRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = get_user(db, user_id=current_user.id)

    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.user_id == user.id, Project.active == True)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    for existing_key in project.api_keys:
        if not existing_key.revoked:
            existing_key.revoked = True
            existing_key.revoked_at = datetime.utcnow()
            db.add(existing_key)

    key, plain_key = create_project_api_key(
        db,
        project=project,
        name=payload.name or "Dashboard project key",
        expires_at=expires_at_from_days(payload.expires_in_days),
    )
    db.commit()
    db.refresh(project)

    return ProjectApiKeyResponse(
        project_id=project.id,
        api_key=plain_key,
        api_key_prefix=key.prefix,
        authorization_header=f"Bearer {plain_key}",
    )


@router.get("", response_model=ProjectManagementListResponse)
def list_projects_with_management_key(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    user, _api_key = authenticate_management_api_key(
        db,
        authorization=authorization,
        request=request,
    )
    projects = (
        db.query(Project)
        .filter(Project.user_id == user.id, Project.active == True)
        .order_by(Project.created_at.desc())
        .all()
    )
    db.commit()
    return ProjectManagementListResponse(projects=[_project_summary(project) for project in projects])


@router.post("", response_model=ProjectManagementCreateResponse, status_code=status.HTTP_201_CREATED)
def create_project_with_management_key(
    payload: ProjectManagementCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    user, _api_key = authenticate_management_api_key(
        db,
        authorization=authorization,
        request=request,
    )
    user, plan = get_user_and_plan(db, user_id=user.id)
    ensure_project_capacity(db, user=user, plan=plan)
    project, api_key, api_key_prefix = _create_project(
        db,
        user=user,
        payload=payload,
        api_key_name=payload.api_key_name or "Agent project key",
        api_key_expires_at=expires_at_from_days(payload.api_key_expires_in_days),
    )
    record_api_key_audit_event(
        db,
        user_id=user.id,
        key_type="management",
        key_prefix=_api_key.prefix,
        action="create_project",
        resource_type="project",
        resource_id=project.id,
        request=request,
    )
    record_api_key_audit_event(
        db,
        user_id=user.id,
        key_type="project",
        key_prefix=api_key_prefix,
        action="create",
        resource_type="project",
        resource_id=project.id,
        request=request,
    )
    db.commit()
    return ProjectManagementCreateResponse(
        project=_project_summary(project),
        api_key=api_key,
        api_key_prefix=api_key_prefix,
        authorization_header=f"Bearer {api_key}",
    )


@router.post("/{project_id}/api-keys", response_model=ProjectApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_project_api_key_with_management_key(
    project_id: str,
    payload: ProjectCreateApiKeyRequest,
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    user, _api_key = authenticate_management_api_key(
        db,
        authorization=authorization,
        request=request,
    )
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user.id, Project.active == True)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    key, plain_key = create_project_api_key(
        db,
        project=project,
        name=payload.name,
        expires_at=expires_at_from_days(payload.expires_in_days),
    )
    record_api_key_audit_event(
        db,
        user_id=user.id,
        key_type="management",
        key_prefix=_api_key.prefix,
        action="create_project_api_key",
        resource_type="project",
        resource_id=project.id,
        request=request,
    )
    record_api_key_audit_event(
        db,
        user_id=user.id,
        key_type="project",
        key_prefix=key.prefix,
        action="create",
        resource_type="project",
        resource_id=project.id,
        request=request,
    )
    db.commit()
    return ProjectApiKeyResponse(
        project_id=project.id,
        api_key=plain_key,
        api_key_prefix=key.prefix,
        authorization_header=f"Bearer {plain_key}",
    )


class ProjectDeleteRequest(BaseModel):
    project_id: str


@router.post("/delete", status_code=status.HTTP_200_OK)
def delete_project(
    payload: ProjectDeleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = get_user(db, user_id=current_user.id)

    # Find the project and verify it belongs to the user
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.user_id == user.id, Project.active == True)
        .first()
    )

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Mark the project as inactive
    project.active = False
    db.add(project)
    db.commit()

    documents = (
        db.query(ProjectDocument)
        .filter(ProjectDocument.project_id == project.id, ProjectDocument.active == True)
        .all()
    )
    vector_store = vector_store_registry.get_vector_store(project)
    for doc in documents:
        try:
            vector_store.delete_document(doc)
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("Failed to delete Vespa document %s", doc.id)
        doc.active = False
        db.add(doc)

    db.commit()

    return {"detail": "Project deleted successfully"}
