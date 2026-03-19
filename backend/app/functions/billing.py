from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from fastapi import HTTPException, status
from polar_sdk import Polar
from polar_sdk.models.order import Order
from polar_sdk.models.subscription import Subscription
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database.models import Plan, User, UserSubscription
from .accounts import apply_plan_limits


def _external_customer_id(user_id: int) -> str:
    return f"user-{user_id}"


@dataclass(frozen=True)
class PolarConfig:
    access_token: str
    environment: str
    success_url: str
    cancel_url: str


def _get_config() -> PolarConfig:
    config = PolarConfig(
        access_token=settings.polar_access_token,
        environment=settings.polar_environment,
        success_url=settings.polar_success_url,
        cancel_url=settings.polar_cancel_url,
    )

    if not config.access_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Polar is not configured")
    return config


def _client(config: PolarConfig) -> Polar:
    return Polar(access_token=config.access_token, server=config.environment)


def _get_plan_by_slug(session: Session, *, plan_slug: str) -> Plan:
    plan = session.execute(select(Plan).where(Plan.slug == plan_slug)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not plan.polar_product_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Plan not configured for billing")
    return plan


def _get_plan_from_subscription_payload(session: Session, *, subscription_payload: Subscription) -> Plan | None:
    product_id = getattr(subscription_payload, "product_id", None)
    if not product_id:
        product = getattr(subscription_payload, "product", None)
        product_id = getattr(product, "id", None)
    if not product_id:
        return None
    return session.execute(select(Plan).where(Plan.polar_product_id == product_id)).scalar_one_or_none()


def create_checkout_session(user: User, plan_slug: str) -> str:
    config = _get_config()
    client = _client(config)

    from ..database import get_db_session

    with get_db_session() as db:
        db_user = db.get(User, user.id)
        if db_user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
        plan = _get_plan_by_slug(db, plan_slug=plan_slug)
        current_subscription = db_user.subscription

        if current_subscription is not None:
            if current_subscription.plan_id == plan.id:
                return settings.polar_portal_return_url
            if current_subscription.polar_subscription_id:
                try:
                    updated_subscription = client.subscriptions.update(
                        id=current_subscription.polar_subscription_id,
                        subscription_update={
                            "product_id": plan.polar_product_id,
                        },
                    )
                except Exception as exc:  # pragma: no cover
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unable to update subscription") from exc

                update_subscription_state(
                    db,
                    user=db_user,
                    subscription_payload=updated_subscription,
                    fallback_plan=plan,
                )
                db.commit()
                return config.success_url
            return create_billing_portal(db_user)

    try:
        checkout = client.checkouts.create(
            request={
                "products": [plan.polar_product_id],
                "external_customer_id": _external_customer_id(user.id),
                "success_url": config.success_url,
                "return_url": config.cancel_url,
                "metadata": {
                    "user_id": str(user.id),
                    "intent": "plan_upgrade",
                    "plan_id": str(plan.id),
                }
            }
        )
        return checkout.url
    except Exception as exc:  # pragma: no cover
        print(exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unable to create checkout session") from exc


def create_billing_portal(user: User) -> str:
    subscription = user.subscription
    if subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription missing")

    config = _get_config()
    client = _client(config)

    try:
        customer_session = client.customer_sessions.create(
            request={
                "external_customer_id": _external_customer_id(user.id),
                "return_url": settings.polar_portal_return_url,
            }
        )
    except Exception as exc:  # pragma: no cover
        if settings.polar_organization_slug:
            return f"https://polar.sh/{settings.polar_organization_slug}/portal"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unable to open Polar billing portal") from exc

    customer_portal_url = getattr(customer_session, "customer_portal_url", None) or getattr(customer_session, "customerPortalUrl", None)
    if not customer_portal_url:
        if settings.polar_organization_slug:
            return f"https://polar.sh/{settings.polar_organization_slug}/portal"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unable to open Polar billing portal")
    return customer_portal_url


def _sync_subscription(subscription_model: UserSubscription, payload: Subscription) -> None:
    subscription_model.polar_subscription_id = payload.id
    subscription_model.polar_customer_id = payload.customer_id
    subscription_model.status = payload.status.value
    subscription_model.current_period_end = payload.current_period_end
    subscription_model.cancel_at_period_end = payload.cancel_at_period_end


def handle_checkout_completed(
    session: Session,
    *,
    order: Order,
    user: User,
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

        subscription = user.subscription
        if subscription is None:
            subscription = UserSubscription(
                user_id=user.id,
                plan_id=target_plan.id,
                status="active",
                polar_customer_id=order.customer_id,
            )
        else:
            subscription.plan_id = target_plan.id
            subscription.status = "active"
            subscription.polar_customer_id = order.customer_id

        # Sync subscription data from Polar if available
        if order.subscription is not None:
            _sync_subscription(subscription, order.subscription)
        elif order.subscription_id:
            subscription.polar_subscription_id = order.subscription_id

        session.add(subscription)
        apply_plan_limits(session, user=user, plan=target_plan)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown checkout intent")


def update_subscription_state(
    session: Session,
    *,
    user: User,
    subscription_payload: Subscription,
    fallback_plan: Plan | None = None,
) -> None:
    user_subscription = user.subscription
    target_plan = _get_plan_from_subscription_payload(session, subscription_payload=subscription_payload) or fallback_plan
    if target_plan is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Subscription plan mapping missing")

    if user_subscription is None:
        user_subscription = UserSubscription(
            user_id=user.id,
            plan_id=target_plan.id,
            status="active",
        )

    user_subscription.plan_id = target_plan.id

    _sync_subscription(user_subscription, subscription_payload)
    session.add(user_subscription)
    apply_plan_limits(session, user=user, plan=target_plan)
