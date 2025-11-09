from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from fastapi import HTTPException, status
from polar_sdk import Polar
from polar_sdk.models.order import Order
from polar_sdk.models.subscription import Subscription
from sqlalchemy.orm import Session

from ..config import settings
from ..database.models import Account, AccountSubscription, Plan
from .accounts import apply_plan_limits


def _external_customer_id(account_id: int) -> str:
    return f"account-{account_id}"


@dataclass(frozen=True)
class PolarConfig:
    access_token: str
    environment: str
    success_url: str
    cancel_url: str
    product_building: str
    product_topup: str
    topup_unit_cents: int


def _get_config() -> PolarConfig:
    config = PolarConfig(
        access_token=settings.polar_access_token,
        environment=settings.polar_environment,
        success_url=settings.polar_success_url,
        cancel_url=settings.polar_cancel_url,
        product_building=settings.polar_product_building,
        product_topup=settings.polar_product_topup,
        topup_unit_cents=settings.polar_topup_unit_cents,
    )

    if not config.access_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Polar is not configured")
    return config


def _client(config: PolarConfig) -> Polar:
    return Polar(access_token=config.access_token, server=config.environment)


def create_upgrade_checkout_session(
    session: Session,
    *,
    account: Account,
    user_email: str,
    target_plan: Plan,
) -> str:
    subscription = account.subscription
    if subscription and subscription.plan_id == target_plan.id and subscription.status == "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Already on the Building plan")

    config = _get_config()
    if not config.product_building:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polar product for Building plan not configured",
        )

    client = _client(config)
    metadata: Dict[str, Any] = {
        "account_id": str(account.id),
        "plan_id": str(target_plan.id),
        "intent": "plan_upgrade",
    }

    checkout = client.checkouts.create(
        request={
            "products": [config.product_building],
            "success_url": config.success_url,
            "return_url": config.cancel_url,
            "external_customer_id": _external_customer_id(account.id),
            "customer_email": user_email,
            "metadata": metadata,
        }
    )

    return checkout.url


def create_topup_checkout_session(
    session: Session,
    *,
    account: Account,
    user_email: str,
    quantity_millions: int,
) -> str:
    if quantity_millions <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Quantity must be positive")

    config = _get_config()
    if not config.product_topup:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Polar product for vector top-ups not configured")
    if config.topup_unit_cents <= 0:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polar top-up unit amount must be configured",
        )

    subscription = account.subscription
    if subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription missing")

    client = _client(config)

    vectors = quantity_millions * 1_000_000
    metadata: Dict[str, Any] = {
        "account_id": str(account.id),
        "intent": "vector_topup",
        "vectors": str(vectors),
        "quantity_millions": str(quantity_millions),
    }

    checkout = client.checkouts.create(
        request={
            "products": [config.product_topup],
            "amount": quantity_millions * config.topup_unit_cents,
            "success_url": config.success_url,
            "return_url": config.cancel_url,
            "external_customer_id": _external_customer_id(account.id),
            "customer_email": user_email,
            "metadata": metadata,
        }
    )

    return checkout.url


def create_billing_portal(account: Account) -> str:
    subscription = account.subscription
    if subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription missing")

    config = _get_config()
    client = _client(config)

    try:
        customer_session = client.customer_sessions.create(
            request={
                "external_customer_id": _external_customer_id(account.id),
                "return_url": settings.polar_portal_return_url,
            }
        )
    except Exception as exc:  # pragma: no cover
        if settings.polar_organization_slug:
            return f"https://polar.sh/{settings.polar_organization_slug}/portal"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unable to open Polar billing portal") from exc

    return customer_session.url


def _sync_subscription(subscription_model: AccountSubscription, payload: Subscription) -> None:
    subscription_model.polar_subscription_id = payload.id
    subscription_model.polar_customer_id = payload.customer_id
    subscription_model.status = payload.status.value
    subscription_model.current_period_end = payload.current_period_end
    subscription_model.cancel_at_period_end = payload.cancel_at_period_end


def handle_checkout_completed(
    session: Session,
    *,
    order: Order,
    account: Account,
    intent: str,
    plan_lookup: Dict[str, Plan],
) -> None:
    if intent == "plan_upgrade":
        # Get plan_id from order metadata
        plan_id = int(order.metadata.get("plan_id"))
        target_plan = plan_lookup.get(str(plan_id)) or next(
            (p for p in plan_lookup.values() if p.id == plan_id), None
        )

        if target_plan is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Target plan not found")

        # Create subscription directly as active after successful payment
        subscription = AccountSubscription(
            account_id=account.id,
            plan_id=target_plan.id,
            status="active",
            polar_customer_id=order.customer_id,
        )

        # Sync subscription data from Polar if available
        if order.subscription is not None:
            _sync_subscription(subscription, order.subscription)
        elif order.subscription_id:
            subscription.polar_subscription_id = order.subscription_id

        session.add(subscription)
        apply_plan_limits(session, account=account, plan=target_plan)
    elif intent == "vector_topup":
        from ..database.models import VectorTopUp

        vectors = int(order.metadata.get("vectors", "0"))
        if vectors <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid vector quantity")
        topup = VectorTopUp(
            account_id=account.id,
            vectors_granted=vectors,
            vectors_remaining=vectors,
            polar_order_id=order.id,
        )
        session.add(topup)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown checkout intent")


def update_subscription_state(
    session: Session,
    *,
    account: Account,
    subscription_payload: Subscription,
) -> None:
    account_subscription = account.subscription
    if account_subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription missing")

    _sync_subscription(account_subscription, subscription_payload)
    session.add(account_subscription)
