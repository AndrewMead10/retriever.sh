from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import (
    User,
    UserSubscription,
    UserUsage,
    Plan,
    Project,
    RateLimitBucket,
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
def seeded_user(session: Session):
    plan = Plan(
        slug="tinkering",
        name="Tinkering",
        price_cents=500,
        query_qps_limit=5,
        ingest_qps_limit=5,
        project_limit=3,
        vector_limit=10_000,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(plan)
    session.flush()

    user = User(email="test@example.com", hashed_password="hashed", is_active=True)
    session.add(user)
    session.flush()

    subscription = UserSubscription(user_id=user.id, plan_id=plan.id, status="active")
    usage = UserUsage(user_id=user.id)
    session.add_all([subscription, usage])
    session.flush()

    bucket = RateLimitBucket(
        user_id=user.id,
        limit_type="query",
        tokens=plan.query_qps_limit,
        last_refill=datetime.utcnow(),
        max_tokens=plan.query_qps_limit,
    )
    session.add(bucket)
    session.commit()
    return user, plan


def test_consume_rate_limit_blocks_when_exhausted(session: Session, seeded_user):
    user, plan = seeded_user

    # Consume the entire bucket.
    result = None
    for _ in range(plan.query_qps_limit):
        result = consume_rate_limit(session, user_id=user.id, limit_type="query")
    assert result is not None and result.remaining <= 1
    session.commit()

    # Immediate additional request should raise 429 due to no refill time.
    with pytest.raises(RateLimitExceeded):
        consume_rate_limit(session, user_id=user.id, limit_type="query")


def test_consume_rate_limit_creates_missing_bucket(session: Session, seeded_user):
    user, plan = seeded_user

    # Seed fixture only creates query bucket; ingest should self-heal.
    result = consume_rate_limit(session, user_id=user.id, limit_type="ingest")
    session.commit()

    ingest_bucket = (
        session.query(RateLimitBucket)
        .filter(RateLimitBucket.user_id == user.id, RateLimitBucket.limit_type == "ingest")
        .one_or_none()
    )

    assert ingest_bucket is not None
    assert ingest_bucket.max_tokens == plan.ingest_qps_limit
    assert result.remaining == float(plan.ingest_qps_limit - 1)


def test_usage_counters_increment_and_vector_capacity(session: Session, seeded_user):
    user, plan = seeded_user

    usage = increment_usage(session, user=user, queries=2, ingests=1, vectors=500)
    session.commit()

    assert usage.total_queries == 2
    assert usage.total_ingest_requests == 1
    assert usage.total_vectors == 500

    project = Project(
        user_id=user.id,
        name="Capacity Test",
        description=None,
        slug="capacity-test",
        embedding_provider="llama.cpp",
        embedding_model="model",
        embedding_model_repo=None,
        embedding_model_file=None,
        embedding_dim=256,
        hybrid_weight_vector=0.5,
        hybrid_weight_text=0.5,
        top_k_default=5,
        vector_search_k=20,
        vector_store_path="proj_capacity",
        vector_count=plan.vector_limit - 1,
        ingest_api_key_hash="hash",
        active=True,
    )
    session.add(project)
    session.flush()

    # Should allow ingesting within the per-project limit
    ensure_vector_capacity(
        session,
        user=user,
        plan=plan,
        additional_vectors=1,
        project=project,
    )

    project.vector_count = plan.vector_limit
    session.add(project)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        ensure_vector_capacity(
            session,
            user=user,
            plan=plan,
            additional_vectors=1,
            project=project,
        )

    assert exc.value.status_code == 402


def test_scale_plan_enforces_per_project_limit(session: Session):
    plan = Plan(
        slug="scale",
        name="Scale",
        price_cents=5_000,
        query_qps_limit=100,
        ingest_qps_limit=100,
        project_limit=-1,
        vector_limit=250_000,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(plan)
    session.flush()

    user = User(email="scale@example.com", hashed_password="hashed", is_active=True)
    session.add(user)
    session.flush()

    subscription = UserSubscription(user_id=user.id, plan_id=plan.id, status="active")
    usage = UserUsage(user_id=user.id)
    session.add_all([subscription, usage])
    session.flush()

    limit = get_per_project_vector_limit(plan)
    assert limit == 250_000

    project = Project(
        user_id=user.id,
        name="Scale Workspace",
        description=None,
        slug="scale-workspace",
        embedding_provider="llama.cpp",
        embedding_model="model",
        embedding_model_repo=None,
        embedding_model_file=None,
        embedding_dim=256,
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
        user=user,
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
            user=user,
            plan=plan,
            additional_vectors=1,
            project=project,
        )

    assert exc.value.status_code == 402
