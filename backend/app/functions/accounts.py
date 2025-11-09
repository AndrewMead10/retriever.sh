from __future__ import annotations

from datetime import datetime
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database.models import Account, AccountSubscription, AccountUsage, Plan, Project, VectorTopUp

PER_PROJECT_VECTOR_LIMITS: dict[str, int] = {
    "scale": 250_000,
}


def get_per_project_vector_limit(plan: Plan) -> int | None:
    return PER_PROJECT_VECTOR_LIMITS.get(plan.slug)


def get_account(session: Session, *, user_id: int) -> Account:
    account = session.execute(
        select(Account).where(Account.owner_user_id == user_id)
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def get_account_and_plan(session: Session, *, user_id: int) -> Tuple[Account, Plan]:
    account = get_account(session, user_id=user_id)
    subscription = account.subscription
    if subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Account subscription missing")

    plan = subscription.plan
    if plan is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription plan missing")

    return account, plan


def get_vector_limit(session: Session, *, account: Account, plan: Plan) -> int | None:
    base_limit = plan.vector_limit
    if base_limit is not None and base_limit < 0:
        base_limit = None

    top_up_total = session.execute(
        select(func.coalesce(func.sum(VectorTopUp.vectors_granted), 0)).where(
            VectorTopUp.account_id == account.id
        )
    ).scalar_one()

    if base_limit is None:
        return None
    return base_limit + (top_up_total or 0)


def get_project_limit(plan: Plan) -> int | None:
    if plan.project_limit is None or plan.project_limit < 0:
        return None
    return plan.project_limit


def ensure_project_capacity(session: Session, *, account: Account, plan: Plan) -> None:
    max_projects = get_project_limit(plan)
    if max_projects is None:
        return
    current_projects = session.execute(
        select(func.count(Project.id)).where(Project.account_id == account.id)
    ).scalar_one()
    if current_projects >= max_projects:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Project limit reached for your plan. Upgrade to add more projects.",
        )


def get_usage(session: Session, *, account: Account) -> AccountUsage:
    usage = account.usage
    if usage is None:
        usage = AccountUsage(account_id=account.id)
        session.add(usage)
        session.flush()
    return usage


def increment_usage(
    session: Session,
    *,
    account: Account,
    queries: int = 0,
    ingests: int = 0,
    vectors: int = 0,
) -> AccountUsage:
    usage = get_usage(session, account=account)
    usage.total_queries += queries
    usage.total_ingest_requests += ingests
    usage.total_vectors += vectors
    usage.updated_at = datetime.utcnow()
    session.add(usage)
    return usage


def decrement_vector_usage(session: Session, *, account: Account, vectors: int) -> AccountUsage:
    usage = get_usage(session, account=account)
    usage.total_vectors = max(0, usage.total_vectors - vectors)
    usage.updated_at = datetime.utcnow()
    session.add(usage)
    return usage


def ensure_vector_capacity(
    session: Session,
    *,
    account: Account,
    plan: Plan,
    additional_vectors: int,
    project: Project | None = None,
) -> None:
    limit = get_vector_limit(session, account=account, plan=plan)
    if limit is not None:
        usage = get_usage(session, account=account)
        if usage.total_vectors + additional_vectors > limit:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                detail="Vector storage limit reached. Upgrade plan or purchase additional capacity.",
            )

    per_project_limit = get_per_project_vector_limit(plan)
    if per_project_limit is not None and project is not None:
        if project.vector_count + additional_vectors > per_project_limit:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                detail="Project vector limit reached. Upgrade to a higher tier or archive vectors to continue.",
            )


def get_plan_by_slug(session: Session, slug: str) -> Plan | None:
    return session.execute(select(Plan).where(Plan.slug == slug)).scalar_one_or_none()


def get_account_by_id(session: Session, account_id: int) -> Account | None:
    return session.get(Account, account_id)


def apply_plan_limits(session: Session, *, account: Account, plan: Plan) -> None:
    now = datetime.utcnow()
    for bucket in account.rate_limit_buckets:
        if bucket.limit_type == "query":
            bucket.max_tokens = plan.query_qps_limit
        elif bucket.limit_type == "ingest":
            bucket.max_tokens = plan.ingest_qps_limit
        else:
            continue

        if bucket.max_tokens <= 0:
            bucket.tokens = float(bucket.max_tokens)
        else:
            bucket.tokens = float(bucket.max_tokens)
        bucket.last_refill = now
        session.add(bucket)
