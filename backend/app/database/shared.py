from sqlalchemy.orm import Session
from .models import (
    Account,
    AccountSubscription,
    AccountUsage,
    Plan,
    RateLimitBucket,
    User,
    PasswordResetToken,
)
from . import get_db_session
from datetime import datetime




def get_user_by_id(user_id: int) -> User | None:
    """Get user by ID"""
    with get_db_session() as db:
        return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(email: str) -> User | None:
    """Get user by email"""
    with get_db_session() as db:
        return db.query(User).filter(User.email == email).first()


def create_user(email: str, hashed_password: str, default_plan_slug: str = "free") -> User:
    """Create a new user"""
    with get_db_session() as db:
        plan = db.query(Plan).filter(Plan.slug == default_plan_slug).one_or_none()
        if plan is None:
            raise ValueError(f"default plan '{default_plan_slug}' is not configured")

        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.flush()

        account = Account(owner_user_id=user.id, name=None)
        db.add(account)
        db.flush()

        subscription = AccountSubscription(account_id=account.id, plan_id=plan.id, status="active")
        db.add(subscription)

        usage = AccountUsage(account_id=account.id)
        db.add(usage)

        query_bucket = RateLimitBucket(
            account_id=account.id,
            limit_type="query",
            tokens=float(plan.query_qps_limit),
            max_tokens=plan.query_qps_limit,
        )
        ingest_bucket = RateLimitBucket(
            account_id=account.id,
            limit_type="ingest",
            tokens=float(plan.ingest_qps_limit),
            max_tokens=plan.ingest_qps_limit,
        )
        db.add_all([query_bucket, ingest_bucket])

        db.commit()
        db.refresh(user)
        return user
