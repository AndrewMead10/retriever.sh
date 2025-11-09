from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import (
    Account,
    AccountSubscription,
    AccountUsage,
    Plan,
    Project,
    RateLimitBucket,
    User,
)
from app.functions.accounts import ensure_vector_capacity, get_per_project_vector_limit, increment_usage
from app.functions.rate_limits import RateLimitExceeded, consume_rate_limit


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine)
    from app.database.models import Base

    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_account(session: Session):
    plan = Plan(
        slug="tinkering",
        name="Tinkering",
        price_cents=500,
        query_qps_limit=1,
        ingest_qps_limit=1,
        project_limit=3,
        vector_limit=30_000,
        allow_topups=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(plan)
    session.flush()

    user = User(email="test@example.com", hashed_password="hashed", is_active=True)
    session.add(user)
    session.flush()

    account = Account(owner_user_id=user.id)
    session.add(account)
    session.flush()

    subscription = AccountSubscription(account_id=account.id, plan_id=plan.id, status="active")
    usage = AccountUsage(account_id=account.id)
    session.add_all([subscription, usage])
    session.flush()

    bucket = RateLimitBucket(
        account_id=account.id,
        limit_type="query",
        tokens=1.0,
        last_refill=datetime.utcnow(),
        max_tokens=1,
    )
    session.add(bucket)
    session.commit()
    return account, plan


def test_consume_rate_limit_blocks_when_exhausted(session: Session, seeded_account):
    account, _ = seeded_account

    # First request should succeed and consume available token.
    result = consume_rate_limit(session, account_id=account.id, limit_type="query")
    assert result.remaining <= 1
    session.commit()

    # Immediate second request should raise 429 due to no refill time.
    with pytest.raises(RateLimitExceeded):
        consume_rate_limit(session, account_id=account.id, limit_type="query")


def test_usage_counters_increment_and_vector_capacity(session: Session, seeded_account):
    account, plan = seeded_account

    usage = increment_usage(session, account=account, queries=2, ingests=1, vectors=500)
    session.commit()

    assert usage.total_queries == 2
    assert usage.total_ingest_requests == 1
    assert usage.total_vectors == 500

    # Filling up to the vector limit should allow but adding one more should fail.
    usage.total_vectors = plan.vector_limit
    session.commit()

    with pytest.raises(HTTPException) as exc:
        ensure_vector_capacity(session, account=account, plan=plan, additional_vectors=1)

    assert exc.value.status_code == 402


def test_scale_plan_enforces_per_project_limit(session: Session):
    plan = Plan(
        slug="scale",
        name="Scale",
        price_cents=5_000,
        query_qps_limit=100,
        ingest_qps_limit=100,
        project_limit=-1,
        vector_limit=-1,
        allow_topups=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(plan)
    session.flush()

    user = User(email="scale@example.com", hashed_password="hashed", is_active=True)
    session.add(user)
    session.flush()

    account = Account(owner_user_id=user.id)
    session.add(account)
    session.flush()

    subscription = AccountSubscription(account_id=account.id, plan_id=plan.id, status="active")
    usage = AccountUsage(account_id=account.id)
    session.add_all([subscription, usage])
    session.flush()

    limit = get_per_project_vector_limit(plan)
    assert limit == 250_000

    project = Project(
        account_id=account.id,
        name="Scale Workspace",
        description=None,
        slug="scale-workspace",
        embedding_provider="llama.cpp",
        embedding_model="model",
        embedding_model_repo=None,
        embedding_model_file=None,
        embedding_dim=768,
        hybrid_weight_vector=0.5,
        hybrid_weight_text=0.5,
        top_k_default=5,
        vector_search_k=20,
        vector_store_path="scale_proj",
        vector_count=limit - 1,
        ingest_api_key_hash="hash",
        active=True,
    )
    session.add(project)
    session.flush()

    # Should allow ingesting the final available vector
    ensure_vector_capacity(
        session,
        account=account,
        plan=plan,
        additional_vectors=1,
        project=project,
    )

    project.vector_count = limit
    session.add(project)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        ensure_vector_capacity(
            session,
            account=account,
            plan=plan,
            additional_vectors=1,
            project=project,
        )

    assert exc.value.status_code == 402
