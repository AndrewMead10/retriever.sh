from __future__ import annotations

from datetime import datetime
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database.models import User, UserSubscription, UserUsage, Plan, Project


def get_per_project_vector_limit(plan: Plan) -> int | None:
    limit = plan.vector_limit
    if limit is None or limit < 0:
        return None
    return limit


def get_user(session: Session, *, user_id: int) -> User:
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_user_and_plan(session: Session, *, user_id: int) -> Tuple[User, Plan]:
    user = get_user(session, user_id=user_id)
    subscription = user.subscription
    if subscription is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User subscription missing")

    plan = subscription.plan
    if plan is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subscription plan missing")

    return user, plan


def get_project_limit(plan: Plan) -> int | None:
    if plan.project_limit is None or plan.project_limit < 0:
        return None
    return plan.project_limit


def ensure_project_capacity(session: Session, *, user: User, plan: Plan) -> None:
    max_projects = get_project_limit(plan)
    if max_projects is None:
        return
    current_projects = session.execute(
        select(func.count(Project.id)).where(Project.user_id == user.id)
    ).scalar_one()
    if current_projects >= max_projects:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Project limit reached for your plan. Upgrade to add more projects.",
        )


def get_usage(session: Session, *, user: User) -> UserUsage:
    usage = user.usage
    if usage is None:
        usage = UserUsage(user_id=user.id)
        session.add(usage)
        session.flush()
    return usage


def increment_usage(
    session: Session,
    *,
    user: User,
    queries: int = 0,
    ingests: int = 0,
    vectors: int = 0,
) -> UserUsage:
    usage = get_usage(session, user=user)
    usage.total_queries += queries
    usage.total_ingest_requests += ingests
    usage.total_vectors += vectors
    usage.updated_at = datetime.utcnow()
    session.add(usage)
    return usage


def decrement_vector_usage(session: Session, *, user: User, vectors: int) -> UserUsage:
    usage = get_usage(session, user=user)
    usage.total_vectors = max(0, usage.total_vectors - vectors)
    usage.updated_at = datetime.utcnow()
    session.add(usage)
    return usage


def ensure_vector_capacity(
    session: Session,
    *,
    user: User,
    plan: Plan,
    additional_vectors: int,
    project: Project | None = None,
) -> None:
    per_project_limit = get_per_project_vector_limit(plan)
    if per_project_limit is not None and project is not None:
        if project.vector_count + additional_vectors > per_project_limit:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                detail="Project vector limit reached. Upgrade to a higher tier or archive vectors to continue.",
            )


def get_plan_by_slug(session: Session, slug: str) -> Plan | None:
    return session.execute(select(Plan).where(Plan.slug == slug)).scalar_one_or_none()


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def apply_plan_limits(session: Session, *, user: User, plan: Plan) -> None:
    now = datetime.utcnow()
    for bucket in user.rate_limit_buckets:
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
