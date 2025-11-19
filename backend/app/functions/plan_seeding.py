from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db_session
from ..database.models import Plan

DEFAULT_PLANS = [
    {
        "slug": "tinkering",
        "name": "Tinkering",
        "price_cents": 500,
        "query_qps_limit": 5,
        "ingest_qps_limit": 5,
        "project_limit": 3,
        "vector_limit": 10_000,
        "polar_product_id": None,
    },
    {
        "slug": "building",
        "name": "Building",
        "price_cents": 2_000,
        "query_qps_limit": 10,
        "ingest_qps_limit": 10,
        "project_limit": 20,
        "vector_limit": 100_000,
        "polar_product_id": None,
    },
    {
        "slug": "scale",
        "name": "Scale",
        "price_cents": 5_000,
        "query_qps_limit": 100,
        "ingest_qps_limit": 100,
        "project_limit": -1,
        "vector_limit": 250_000,
        "polar_product_id": None,
    },
]


def seed_plans(session: Session) -> None:
    """Ensure the canonical plan definitions exist."""
    now = datetime.utcnow()
    existing_rows = list(session.execute(select(Plan)).scalars())
    slug_map = {row.slug: row for row in existing_rows}

    legacy_slug_map = {
        "free": "tinkering",
        "testing": "tinkering",
        "pro": "building",
        "enterprise": "scale",
    }

    changed = False
    for legacy_slug, new_slug in legacy_slug_map.items():
        if legacy_slug in slug_map and new_slug not in slug_map:
            plan = slug_map.pop(legacy_slug)
            plan.slug = new_slug
            plan.updated_at = now
            session.add(plan)
            slug_map[new_slug] = plan
            changed = True

    existing = {
        row.slug: row
        for row in slug_map.values()
    }

    for base_plan_data in DEFAULT_PLANS:
        plan_data = dict(base_plan_data)
        if plan_data["slug"] == "tinkering" and settings.polar_product_tinkering:
            plan_data["polar_product_id"] = settings.polar_product_tinkering
        if plan_data["slug"] == "building" and settings.polar_product_building:
            plan_data["polar_product_id"] = settings.polar_product_building
        if plan_data["slug"] == "scale" and settings.polar_product_scale:
            plan_data["polar_product_id"] = settings.polar_product_scale
        plan = existing.get(plan_data["slug"])
        if plan is None:
            session.add(Plan(**plan_data, created_at=now, updated_at=now))
            changed = True
        else:
            updated = False
            for key, value in plan_data.items():
                if getattr(plan, key) != value:
                    setattr(plan, key, value)
                    updated = True
            if updated:
                plan.updated_at = now
                changed = True

    if changed:
        session.commit()
