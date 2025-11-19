"""update plan vector limits to per-project values

Revision ID: 0007_per_project_vector_limits
Revises: 0006_remove_account_tables
Create Date: 2025-11-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_per_project_vector_limits"
down_revision = "0006_remove_account_tables"
branch_labels = None
depends_on = None


PLAN_LIMITS = {
    "tinkering": 10_000,
    "building": 100_000,
    "scale": 250_000,
    # legacy slugs kept in sync for older records
    "free": 10_000,
    "testing": 10_000,
    "pro": 100_000,
    "enterprise": 250_000,
}


LEGACY_TOTAL_LIMITS = {
    "tinkering": 30_000,
    "building": 2_000_000,
    "scale": -1,
    "free": 30_000,
    "testing": 30_000,
    "pro": 2_000_000,
    "enterprise": -1,
}


def _update_limits(limits: dict[str, int]) -> None:
    conn = op.get_bind()
    for slug, limit in limits.items():
        conn.execute(
            sa.text("UPDATE plans SET vector_limit = :limit WHERE slug = :slug"),
            {"limit": limit, "slug": slug},
        )


def upgrade() -> None:
    _update_limits(PLAN_LIMITS)


def downgrade() -> None:
    _update_limits(LEGACY_TOTAL_LIMITS)
