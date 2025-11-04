"""account and plan scaffolding

Revision ID: 0002_account_plan_structures
Revises: 0001_init
Create Date: 2025-10-27 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "0002_account_plan_structures"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )
    op.create_index("ix_accounts_owner_user_id", "accounts", ["owner_user_id"], unique=True)

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("stripe_price_id", sa.String(), nullable=True),
        sa.Column("query_qps_limit", sa.Integer(), nullable=False),
        sa.Column("ingest_qps_limit", sa.Integer(), nullable=False),
        sa.Column("project_limit", sa.Integer(), nullable=False),
        sa.Column("vector_limit", sa.Integer(), nullable=False),
        sa.Column("allow_topups", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )

    op.create_table(
        "account_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False, unique=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )
    op.create_index("ix_account_subscriptions_account_id", "account_subscriptions", ["account_id"], unique=True)

    op.create_table(
        "vector_top_ups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("vectors_granted", sa.Integer(), nullable=False),
        sa.Column("vectors_remaining", sa.Integer(), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),
        sa.Column("purchased_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )
    op.create_index("ix_vector_top_ups_account_id", "vector_top_ups", ["account_id"])

    op.create_table(
        "account_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False, unique=True),
        sa.Column("total_queries", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_ingest_requests", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_vectors", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_reset", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )
    op.create_index("ix_account_usage_account_id", "account_usage", ["account_id"], unique=True)

    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("limit_type", sa.String(), nullable=False),
        sa.Column("tokens", sa.Float(), nullable=False),
        sa.Column("last_refill", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.UniqueConstraint("account_id", "limit_type", name="uq_rate_limit_account_type"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("embedding_provider", sa.String(), nullable=False),
        sa.Column("embedding_model", sa.String(), nullable=False),
        sa.Column("embedding_model_repo", sa.String(), nullable=True),
        sa.Column("embedding_model_file", sa.String(), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("hybrid_weight_vector", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("hybrid_weight_text", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("top_k_default", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("vector_search_k", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("vector_store_path", sa.String(), nullable=False),
        sa.Column("vector_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ingest_api_key_hash", sa.String(), nullable=False),
        sa.Column("last_ingest_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.UniqueConstraint("account_id", "name", name="uq_projects_account_name"),
    )
    op.create_index("ix_projects_account_id", "projects", ["account_id"])

    op.create_table(
        "project_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("prefix", sa.String(), nullable=False),
        sa.Column("hashed_key", sa.String(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )
    op.create_index("ix_project_api_keys_project_id", "project_api_keys", ["project_id"])

    op.create_table(
        "scale_plan_inquiries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )
    op.create_index("ix_scale_plan_inquiries_user_id", "scale_plan_inquiries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_scale_plan_inquiries_user_id", table_name="scale_plan_inquiries")
    op.drop_table("scale_plan_inquiries")

    op.drop_index("ix_project_api_keys_project_id", table_name="project_api_keys")
    op.drop_table("project_api_keys")

    op.drop_constraint("uq_projects_account_name", "projects", type_="unique")
    op.drop_index("ix_projects_account_id", table_name="projects")
    op.drop_table("projects")

    op.drop_constraint("uq_rate_limit_account_type", "rate_limit_buckets", type_="unique")
    op.drop_table("rate_limit_buckets")

    op.drop_index("ix_account_usage_account_id", table_name="account_usage")
    op.drop_table("account_usage")

    op.drop_index("ix_vector_top_ups_account_id", table_name="vector_top_ups")
    op.drop_table("vector_top_ups")

    op.drop_index("ix_account_subscriptions_account_id", table_name="account_subscriptions")
    op.drop_table("account_subscriptions")

    op.drop_table("plans")

    op.drop_index("ix_accounts_owner_user_id", table_name="accounts")
    op.drop_table("accounts")
