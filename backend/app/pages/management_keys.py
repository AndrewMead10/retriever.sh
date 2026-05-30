from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..database.models import ManagementApiKey
from ..functions.accounts import get_user
from ..functions.api_keys import (
    create_management_api_key,
    expires_at_from_days,
    record_api_key_audit_event,
)
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/management-keys", tags=["management-keys"])


class ManagementApiKeySummary(BaseModel):
    id: int
    name: str
    prefix: str
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked: bool
    created_at: datetime


class ManagementKeysOnloadResponse(BaseModel):
    keys: List[ManagementApiKeySummary]


class ManagementApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3660)


class ManagementApiKeyCreateResponse(BaseModel):
    key: ManagementApiKeySummary
    api_key: str
    authorization_header: str


class ManagementApiKeyRevokeRequest(BaseModel):
    key_id: int


def _key_summary(api_key: ManagementApiKey) -> ManagementApiKeySummary:
    return ManagementApiKeySummary(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        revoked=api_key.revoked,
        created_at=api_key.created_at,
    )


@router.get("/onload", response_model=ManagementKeysOnloadResponse)
def management_keys_onload(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = get_user(db, user_id=current_user.id)
    keys = (
        db.query(ManagementApiKey)
        .filter(ManagementApiKey.user_id == user.id)
        .order_by(ManagementApiKey.created_at.desc())
        .all()
    )
    return ManagementKeysOnloadResponse(keys=[_key_summary(key) for key in keys])


@router.post(
    "/onsubmit",
    response_model=ManagementApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_management_key(
    payload: ManagementApiKeyCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = get_user(db, user_id=current_user.id)
    api_key, plain_key = create_management_api_key(
        db,
        user_id=user.id,
        name=payload.name,
        expires_at=expires_at_from_days(payload.expires_in_days),
    )
    record_api_key_audit_event(
        db,
        user_id=user.id,
        key_type="management",
        key_prefix=api_key.prefix,
        action="create",
        resource_type="management_api_key",
        resource_id=str(api_key.id),
        request=request,
    )
    db.commit()
    db.refresh(api_key)
    return ManagementApiKeyCreateResponse(
        key=_key_summary(api_key),
        api_key=plain_key,
        authorization_header=f"Bearer {plain_key}",
    )


@router.post("/revoke")
def revoke_management_key(
    payload: ManagementApiKeyRevokeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = get_user(db, user_id=current_user.id)
    api_key = (
        db.query(ManagementApiKey)
        .filter(ManagementApiKey.id == payload.key_id, ManagementApiKey.user_id == user.id)
        .first()
    )
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Management API key not found")
    if not api_key.revoked:
        api_key.revoked = True
        api_key.revoked_at = datetime.utcnow()
        db.add(api_key)
        record_api_key_audit_event(
            db,
            user_id=user.id,
            key_type="management",
            key_prefix=api_key.prefix,
            action="revoke",
            resource_type="management_api_key",
            resource_id=str(api_key.id),
            request=request,
        )
        db.commit()
    return {"detail": "Management API key revoked"}
