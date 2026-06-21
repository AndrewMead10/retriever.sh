from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database.models import ApiKeyAuditEvent, ManagementApiKey, Project, ProjectApiKey, User


def generate_api_key(prefix: str = "rag") -> str:
    random_part = secrets.token_urlsafe(32).replace("-", "").replace("_", "")
    return f"{prefix}_{random_part}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def key_prefix(key: str, length: int = 10) -> str:
    return key[:length]


def verify_api_key(stored_hash: str, candidate: str) -> bool:
    candidate_hash = hash_api_key(candidate)
    # Use secrets.compare_digest for timing-safe comparison
    return secrets.compare_digest(stored_hash, candidate_hash)


def expires_at_from_days(expires_in_days: Optional[int]) -> datetime | None:
    if expires_in_days is None:
        return None
    return datetime.utcnow() + timedelta(days=expires_in_days)


def parse_bearer_token(authorization: str | None, *, key_type: str = "API key") -> str:
    if not authorization:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=f"Authorization: Bearer <{key_type.lower().replace(' ', '_')}> is required",
        )

    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=f"Authorization header must use Bearer <{key_type.lower().replace(' ', '_')}>",
        )
    return parts[1].strip()


def create_project_api_key(
    db: Session,
    *,
    project: Project,
    name: str = "Default API key",
    expires_at: datetime | None = None,
) -> tuple[ProjectApiKey, str]:
    plain_key = generate_api_key(prefix="retr_proj")
    api_key = ProjectApiKey(
        project_id=project.id,
        name=name.strip() or "Default API key",
        prefix=key_prefix(plain_key),
        hashed_key=hash_api_key(plain_key),
        expires_at=expires_at,
    )
    db.add(api_key)
    db.flush()
    return api_key, plain_key


def create_management_api_key(
    db: Session,
    *,
    user_id: int,
    name: str,
    expires_at: datetime | None = None,
) -> tuple[ManagementApiKey, str]:
    plain_key = generate_api_key(prefix="retr_mgmt")
    api_key = ManagementApiKey(
        user_id=user_id,
        name=name.strip() or "Agent management key",
        prefix=key_prefix(plain_key),
        hashed_key=hash_api_key(plain_key),
        expires_at=expires_at,
    )
    db.add(api_key)
    db.flush()
    return api_key, plain_key


def authenticate_project_api_key(
    db: Session,
    *,
    project: Project,
    authorization: str | None,
) -> ProjectApiKey:
    token = parse_bearer_token(authorization, key_type="project API key")
    candidate_hash = hash_api_key(token)
    api_key = (
        db.query(ProjectApiKey)
        .filter(ProjectApiKey.project_id == project.id, ProjectApiKey.hashed_key == candidate_hash)
        .first()
    )
    if api_key is None or not verify_api_key(api_key.hashed_key, token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid project API key")
    if api_key.revoked or api_key.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="API key has been revoked")
    if api_key.expires_at is not None and api_key.expires_at <= datetime.utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="API key has expired")

    return api_key


def authenticate_management_api_key(
    db: Session,
    *,
    authorization: str | None,
    request: Request | None = None,
) -> tuple[User, ManagementApiKey]:
    token = parse_bearer_token(authorization, key_type="management API key")
    candidate_hash = hash_api_key(token)
    api_key = (
        db.query(ManagementApiKey)
        .filter(ManagementApiKey.hashed_key == candidate_hash)
        .first()
    )
    if api_key is None or not verify_api_key(api_key.hashed_key, token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid management API key")
    if api_key.revoked or api_key.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Management API key has been revoked")
    if api_key.expires_at is not None and api_key.expires_at <= datetime.utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Management API key has expired")

    user = db.query(User).filter(User.id == api_key.user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Management API key owner is inactive")

    api_key.last_used_at = datetime.utcnow()
    db.add(api_key)
    db.flush()
    return user, api_key


def record_api_key_audit_event(
    db: Session,
    *,
    user_id: int,
    key_type: str,
    action: str,
    key_prefix: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request: Request | None = None,
) -> None:
    ip_address = None
    user_agent = None
    if request is not None:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    db.add(
        ApiKeyAuditEvent(
            user_id=user_id,
            key_type=key_type,
            key_prefix=key_prefix,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    db.flush()
