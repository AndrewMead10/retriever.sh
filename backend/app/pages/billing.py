from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, get_db_session
from ..database.models import Plan
from ..functions.accounts import (
    get_account,
    get_account_and_plan,
    get_account_by_id,
)
from ..functions.billing import (
    create_billing_portal,
    create_checkout_session,
    handle_checkout_completed,
    update_subscription_state,
)
from ..middleware.auth import get_current_user
from polar_sdk import webhooks as polar_webhooks

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutResponse(BaseModel):
    url: str


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    plan_slug: str = Query(..., description="Plan slug for checkout"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = get_account(db, user_id=current_user.id)
    url = create_checkout_session(account, plan_slug)
    return CheckoutResponse(url=url)


@router.post("/portal", response_model=CheckoutResponse)
def open_billing_portal(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account, _ = get_account_and_plan(db, user_id=current_user.id)
    url = create_billing_portal(account)
    return CheckoutResponse(url=url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def polar_webhook(
    request: Request,
    polar_signature: Optional[str] = Header(None, alias="Polar-Signature"),
):
    payload = await request.body()

    if not settings.polar_webhook_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Polar webhook secret not configured")

    headers = {"Polar-Signature": polar_signature or ""}
    try:
        event = polar_webhooks.validate_event(payload, headers, settings.polar_webhook_secret)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook payload: {exc}") from exc

    event_dump = event.model_dump()
    event_type = event_dump.get("type")
    data = event_dump.get("data")

    if event_type == "order.paid":
        metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
        account_id = metadata.get("account_id")
        intent = metadata.get("intent")
        if not account_id or not intent:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing metadata on Polar order")

        with get_db_session() as db:
            account = get_account_by_id(db, int(account_id))
            if account is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found for webhook")

            plan_lookup = {plan.slug: plan for plan in db.execute(select(Plan)).scalars()}
            order = event.data  # type: ignore[attr-defined]
            handle_checkout_completed(
                db,
                order=order,
                account=account,
                intent=intent,
                plan_lookup=plan_lookup,
            )
            db.commit()

    elif event_type in {"subscription.updated", "subscription.active", "subscription.uncanceled"}:
        metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
        account_id = metadata.get("account_id")
        if not account_id:
            return {"received": True}

        with get_db_session() as db:
            account = get_account_by_id(db, int(account_id))
            if account is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found for webhook")

            subscription_payload = event.data  # type: ignore[attr-defined]
            update_subscription_state(
                db,
                account=account,
                subscription_payload=subscription_payload,
            )
            db.commit()

    elif event_type in {"subscription.canceled", "subscription.revoked"}:
        metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
        account_id = metadata.get("account_id")
        if not account_id:
            return {"received": True}

        with get_db_session() as db:
            account = get_account_by_id(db, int(account_id))
            if account and account.subscription:
                account.subscription.status = "canceled"
                account.subscription.cancel_at_period_end = True
                db.add(account.subscription)
                db.commit()

    return {"received": True}
