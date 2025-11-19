from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, get_db_session
from ..database.models import Plan
from ..functions.accounts import (
    get_user,
    get_user_and_plan,
    get_user_by_id,
)
from ..functions.billing import (
    create_billing_portal,
    create_checkout_session,
    handle_checkout_completed,
    update_subscription_state,
)
from ..middleware.auth import get_current_user
from polar_sdk import webhooks as polar_webhooks


def _extract_metadata(payload: Any) -> dict[str, Any]:
    """Return metadata dict from Polar payload objects or raw dicts."""
    if payload is None:
        return {}

    if isinstance(payload, dict):
        metadata = payload.get("metadata") or {}
    else:
        metadata = getattr(payload, "metadata", None) or {}

    if isinstance(metadata, dict):
        return metadata
    # Some SDK models may expose metadata as custom mapping types.
    try:
        return dict(metadata)
    except Exception:  # pragma: no cover - defensive
        return {}

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutResponse(BaseModel):
    url: str


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    plan_slug: str = Query(..., description="Plan slug for checkout"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = get_user(db, user_id=current_user.id)
    url = create_checkout_session(user, plan_slug)
    return CheckoutResponse(url=url)


@router.post("/portal", response_model=CheckoutResponse)
def open_billing_portal(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user, _ = get_user_and_plan(db, user_id=current_user.id)
    url = create_billing_portal(user)
    return CheckoutResponse(url=url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def polar_webhook(
    request: Request,
    polar_signature: Optional[str] = Header(None, alias="Polar-Signature"),
    webhook_signature: Optional[str] = Header(None, alias="Webhook-Signature"),
    webhook_id: Optional[str] = Header(None, alias="Webhook-Id"),
    webhook_timestamp: Optional[str] = Header(None, alias="Webhook-Timestamp"),
):
    payload = await request.body()

    if not settings.polar_webhook_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Polar webhook secret not configured")

    # Polar emits Standard Webhooks headers (webhook-id/timestamp/signature).
    # Some legacy configs used Polar-Signature, so fall back to that if needed.
    verification_headers = {
        "webhook-id": webhook_id or request.headers.get("webhook-id"),
        "webhook-timestamp": webhook_timestamp or request.headers.get("webhook-timestamp"),
        "webhook-signature": (webhook_signature or polar_signature or request.headers.get("webhook-signature") or request.headers.get("polar-signature")),
    }

    missing = [name for name, value in verification_headers.items() if not value]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook payload: Missing headers: {', '.join(missing)}",
        )

    try:
        event = polar_webhooks.validate_event(payload, verification_headers, settings.polar_webhook_secret)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook payload: {exc}") from exc

    event_type = getattr(event, "TYPE", None) or event.model_dump(by_alias=True).get("type")
    data = event.data

    if event_type == "order.paid":
        metadata = _extract_metadata(data)
        user_id = metadata.get("user_id")
        intent = metadata.get("intent")
        if not user_id or not intent:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing metadata on Polar order")

        with get_db_session() as db:
            user = get_user_by_id(db, int(user_id))
            if user is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found for webhook")

            plan_lookup = {plan.slug: plan for plan in db.execute(select(Plan)).scalars()}
            order = data
            handle_checkout_completed(
                db,
                order=order,
                user=user,
                intent=intent,
                plan_lookup=plan_lookup,
            )
            db.commit()

    elif event_type in {"subscription.updated", "subscription.active", "subscription.uncanceled"}:
        metadata = _extract_metadata(data.metadata) if hasattr(data, 'metadata') else _extract_metadata(data.get("metadata") if isinstance(data, dict) else {})
        user_id = metadata.get("user_id")
        if not user_id:
            return {"received": True}

        with get_db_session() as db:
            user = get_user_by_id(db, int(user_id))
            if user is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found for webhook")

            subscription_payload = data
            update_subscription_state(
                db,
                user=user,
                subscription_payload=subscription_payload,
            )
            db.commit()

    elif event_type in {"subscription.canceled", "subscription.revoked"}:
        metadata = _extract_metadata(data.metadata) if hasattr(data, 'metadata') else _extract_metadata(data.get("metadata") if isinstance(data, dict) else {})
        user_id = metadata.get("user_id")
        if not user_id:
            return {"received": True}

        with get_db_session() as db:
            user = get_user_by_id(db, int(user_id))
            if user and user.subscription:
                user.subscription.status = "canceled"
                user.subscription.cancel_at_period_end = True
                db.add(user.subscription)
                db.commit()

    return {"received": True}
