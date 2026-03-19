from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.models import Base, Plan, RateLimitBucket, User, UserSubscription
from app.functions.billing import create_checkout_session
from app.pages.billing import _resolve_webhook_user


class _StubPolarClient:
    def __init__(
        self,
        *,
        subscription_response=None,
        checkout_url: str = "https://polar.example/checkout",
        portal_url: str = "https://polar.example/portal",
    ) -> None:
        self.subscription_response = subscription_response
        self.checkout_url = checkout_url
        self.portal_url = portal_url
        self.subscription_update_calls: list[tuple[str, dict[str, str]]] = []
        self.checkout_calls: list[dict[str, object]] = []
        self.customer_session_calls: list[dict[str, object]] = []
        self.subscriptions = SimpleNamespace(update=self._update_subscription)
        self.checkouts = SimpleNamespace(create=self._create_checkout)
        self.customer_sessions = SimpleNamespace(create=self._create_customer_session)

    def _update_subscription(self, *, id: str, subscription_update: dict[str, str]):
        self.subscription_update_calls.append((id, subscription_update))
        if self.subscription_response is None:
            raise AssertionError("subscriptions.update should not be called in this test")
        return self.subscription_response

    def _create_checkout(self, *, request: dict[str, object]):
        self.checkout_calls.append(request)
        return SimpleNamespace(url=self.checkout_url)

    def _create_customer_session(self, *, request: dict[str, object]):
        self.customer_session_calls.append(request)
        return SimpleNamespace(customer_portal_url=self.portal_url)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _seed_plan(
    session: Session,
    *,
    slug: str,
    product_id: str,
    query_limit: int,
    ingest_limit: int,
) -> Plan:
    plan = Plan(
        slug=slug,
        name=slug.title(),
        price_cents=500,
        polar_product_id=product_id,
        query_qps_limit=query_limit,
        ingest_qps_limit=ingest_limit,
        project_limit=3,
        vector_limit=10_000,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(plan)
    session.flush()
    return plan


def _seed_user(session: Session, *, email: str = "billing@example.com") -> User:
    user = User(
        email=email,
        hashed_password="hashed",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(user)
    session.flush()
    return user


def _seed_rate_limit_buckets(session: Session, *, user_id: int, query_limit: int, ingest_limit: int) -> None:
    session.add_all(
        [
            RateLimitBucket(
                user_id=user_id,
                limit_type="query",
                tokens=float(query_limit),
                last_refill=datetime.utcnow(),
                max_tokens=query_limit,
            ),
            RateLimitBucket(
                user_id=user_id,
                limit_type="ingest",
                tokens=float(ingest_limit),
                last_refill=datetime.utcnow(),
                max_tokens=ingest_limit,
            ),
        ]
    )
    session.flush()


def test_create_checkout_session_redirects_existing_subscription_to_portal(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    tinkering = _seed_plan(
        session,
        slug="tinkering",
        product_id="prod_tinkering",
        query_limit=5,
        ingest_limit=5,
    )
    building = _seed_plan(
        session,
        slug="building",
        product_id="prod_building",
        query_limit=10,
        ingest_limit=10,
    )
    user = _seed_user(session)
    session.add(
        UserSubscription(
            user_id=user.id,
            plan_id=tinkering.id,
            status="active",
            polar_customer_id="cust_123",
            polar_subscription_id="sub_123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    _seed_rate_limit_buckets(session, user_id=user.id, query_limit=tinkering.query_qps_limit, ingest_limit=tinkering.ingest_qps_limit)
    session.commit()

    stub_client = _StubPolarClient()

    @contextmanager
    def _get_db_session():
        yield session

    import app.database
    import app.functions.billing as billing_module

    monkeypatch.setattr(app.database, "get_db_session", _get_db_session)
    monkeypatch.setattr(billing_module, "_client", lambda _config: stub_client)

    url = create_checkout_session(user, "building")
    session.refresh(user)

    query_bucket = next(bucket for bucket in user.rate_limit_buckets if bucket.limit_type == "query")
    ingest_bucket = next(bucket for bucket in user.rate_limit_buckets if bucket.limit_type == "ingest")

    assert url == "https://polar.example/portal"
    assert stub_client.subscription_update_calls == []
    assert stub_client.checkout_calls == []
    assert stub_client.customer_session_calls == [
        {
            "external_customer_id": f"user-{user.id}",
            "return_url": settings.polar_portal_return_url,
        }
    ]
    assert user.subscription is not None
    assert user.subscription.plan_id == tinkering.id
    assert query_bucket.max_tokens == tinkering.query_qps_limit
    assert ingest_bucket.max_tokens == tinkering.ingest_qps_limit


def test_create_checkout_session_creates_checkout_for_new_subscription(session: Session, monkeypatch: pytest.MonkeyPatch):
    building = _seed_plan(
        session,
        slug="building",
        product_id="prod_building",
        query_limit=10,
        ingest_limit=10,
    )
    user = _seed_user(session, email="new-billing@example.com")
    session.commit()

    stub_client = _StubPolarClient()

    @contextmanager
    def _get_db_session():
        yield session

    import app.database
    import app.functions.billing as billing_module

    monkeypatch.setattr(app.database, "get_db_session", _get_db_session)
    monkeypatch.setattr(billing_module, "_client", lambda _config: stub_client)

    url = create_checkout_session(user, "building")

    assert url == "https://polar.example/checkout"
    assert stub_client.subscription_update_calls == []
    assert stub_client.checkout_calls == [
        {
            "products": [building.polar_product_id],
            "external_customer_id": f"user-{user.id}",
            "success_url": settings.polar_success_url,
            "return_url": settings.polar_cancel_url,
            "metadata": {
                "user_id": str(user.id),
                "intent": "plan_upgrade",
                "plan_id": str(building.id),
            },
        }
    ]


def test_create_checkout_session_falls_back_to_portal_when_subscription_id_missing(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    tinkering = _seed_plan(
        session,
        slug="tinkering",
        product_id="prod_tinkering",
        query_limit=5,
        ingest_limit=5,
    )
    building = _seed_plan(
        session,
        slug="building",
        product_id="prod_building",
        query_limit=10,
        ingest_limit=10,
    )
    user = _seed_user(session, email="portal-fallback@example.com")
    session.add(
        UserSubscription(
            user_id=user.id,
            plan_id=tinkering.id,
            status="active",
            polar_customer_id="cust_456",
            polar_subscription_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    session.commit()

    stub_client = _StubPolarClient()

    @contextmanager
    def _get_db_session():
        yield session

    import app.database
    import app.functions.billing as billing_module

    monkeypatch.setattr(app.database, "get_db_session", _get_db_session)
    monkeypatch.setattr(billing_module, "_client", lambda _config: stub_client)

    url = create_checkout_session(user, "building")

    assert url == "https://polar.example/portal"
    assert stub_client.subscription_update_calls == []
    assert stub_client.checkout_calls == []
    assert stub_client.customer_session_calls == [
        {
            "external_customer_id": f"user-{user.id}",
            "return_url": settings.polar_portal_return_url,
        }
    ]


def test_resolve_webhook_user_falls_back_to_subscription_id(session: Session):
    plan = _seed_plan(
        session,
        slug="tinkering",
        product_id="prod_tinkering",
        query_limit=5,
        ingest_limit=5,
    )
    user = _seed_user(session, email="webhook@example.com")
    session.add(
        UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            polar_customer_id="cust_999",
            polar_subscription_id="sub_999",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    session.commit()

    payload = SimpleNamespace(id="sub_999", customer_id="cust_999", metadata=None)

    resolved_user = _resolve_webhook_user(session, payload)

    assert resolved_user is not None
    assert resolved_user.id == user.id
