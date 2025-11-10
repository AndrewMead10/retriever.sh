"""remove account tables and migrate to user

Revision ID: 0006_remove_account_tables
Revises: 0004_remove_vector_topups, 0005_add_active_columns
Create Date: 2025-11-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_remove_account_tables"
down_revision = ("0004_remove_vector_topups", "0005_add_active_columns")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column("users", sa.Column("name", sa.String(), nullable=True))

    # Create new user_subscriptions table
    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("polar_customer_id", sa.String(), nullable=True),
        sa.Column("polar_subscription_id", sa.String(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_subscriptions_created_at"), "user_subscriptions", ["created_at"])

    # Create new user_usage table
    op.create_table(
        "user_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_ingest_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_vectors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reset", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_usage_created_at"), "user_usage", ["created_at"])

    # Migrate data from account_subscriptions to user_subscriptions
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO user_subscriptions (user_id, plan_id, status, polar_customer_id, polar_subscription_id, current_period_end, cancel_at_period_end, created_at, updated_at)
        SELECT a.owner_user_id, acs.plan_id, acs.status, acs.polar_customer_id, acs.polar_subscription_id, acs.current_period_end, acs.cancel_at_period_end, acs.created_at, acs.updated_at
        FROM account_subscriptions acs
        JOIN accounts a ON acs.account_id = a.id
    """))

    # Migrate data from account_usage to user_usage
    conn.execute(sa.text("""
        INSERT INTO user_usage (user_id, total_queries, total_ingest_requests, total_vectors, last_reset, created_at, updated_at)
        SELECT a.owner_user_id, au.total_queries, au.total_ingest_requests, au.total_vectors, au.last_reset, au.created_at, au.updated_at
        FROM account_usage au
        JOIN accounts a ON au.account_id = a.id
    """))

    # Migrate user names from accounts table
    conn.execute(sa.text("""
        UPDATE users
        SET name = accounts.name
        FROM accounts
        WHERE users.id = accounts.owner_user_id
    """))

    # Update projects to reference user_id instead of account_id
    op.add_column("projects", sa.Column("user_id", sa.Integer(), nullable=True))
    conn.execute(sa.text("""
        UPDATE projects
        SET user_id = accounts.owner_user_id
        FROM accounts
        WHERE projects.account_id = accounts.id
    """))

    # Make user_id non-nullable and add foreign key
    op.alter_column("projects", "user_id", nullable=False)
    op.create_foreign_key(None, "projects", "users", ["user_id"], ["id"])

    # Update rate_limit_buckets to reference user_id instead of account_id
    op.add_column("rate_limit_buckets", sa.Column("user_id", sa.Integer(), nullable=True))
    conn.execute(sa.text("""
        UPDATE rate_limit_buckets
        SET user_id = accounts.owner_user_id
        FROM accounts
        WHERE rate_limit_buckets.account_id = accounts.id
    """))

    # Make user_id non-nullable and add foreign key
    op.alter_column("rate_limit_buckets", "user_id", nullable=False)
    op.create_foreign_key(None, "rate_limit_buckets", "users", ["user_id"], ["id"])

    # Update vector_top_ups to reference user_id instead of account_id (if the table exists)
    table_exists = conn.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'vector_top_ups')")
    ).scalar()

    if table_exists:
        op.add_column("vector_top_ups", sa.Column("user_id", sa.Integer(), nullable=True))
        conn.execute(sa.text("""
            UPDATE vector_top_ups
            SET user_id = accounts.owner_user_id
            FROM accounts
            WHERE vector_top_ups.account_id = accounts.id
        """))
        op.alter_column("vector_top_ups", "user_id", nullable=False)
        op.create_foreign_key(None, "vector_top_ups", "users", ["user_id"], ["id"])
        op.drop_constraint("vector_top_ups_account_id_fkey", "vector_top_ups", type_="foreignkey")
        op.drop_column("vector_top_ups", "account_id")

    # Drop old constraints and columns
    op.drop_constraint("uq_rate_limit_account_type", "rate_limit_buckets", type_="unique")
    op.create_unique_constraint("uq_rate_limit_user_type", "rate_limit_buckets", ["user_id", "limit_type"])
    op.drop_constraint("rate_limit_buckets_account_id_fkey", "rate_limit_buckets", type_="foreignkey")
    op.drop_column("rate_limit_buckets", "account_id")

    op.drop_constraint("projects_account_id_fkey", "projects", type_="foreignkey")
    op.drop_column("projects", "account_id")

    # Drop old tables
    op.drop_table("account_subscriptions")
    op.drop_table("account_usage")
    op.drop_table("accounts")


def downgrade() -> None:
    # Recreate accounts table
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.UniqueConstraint("owner_user_id"),
    )
    op.create_index(op.f("ix_accounts_created_at"), "accounts", ["created_at"])

    # Recreate account_subscriptions table
    op.create_table(
        "account_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("polar_customer_id", sa.String(), nullable=True),
        sa.Column("polar_subscription_id", sa.String(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.UniqueConstraint("account_id"),
    )
    op.create_index(op.f("ix_account_subscriptions_created_at"), "account_subscriptions", ["created_at"])

    # Recreate account_usage table
    op.create_table(
        "account_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("total_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_ingest_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_vectors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reset", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.UniqueConstraint("account_id"),
    )
    op.create_index(op.f("ix_account_usage_created_at"), "account_usage", ["created_at"])

    # Migrate data back
    conn = op.get_bind()

    # Recreate accounts from users
    conn.execute(sa.text("""
        INSERT INTO accounts (owner_user_id, name, created_at, updated_at)
        SELECT id, name, created_at, updated_at
        FROM users
    """))

    # Migrate subscriptions back
    conn.execute(sa.text("""
        INSERT INTO account_subscriptions (account_id, plan_id, status, polar_customer_id, polar_subscription_id, current_period_end, cancel_at_period_end, created_at, updated_at)
        SELECT a.id, us.plan_id, us.status, us.polar_customer_id, us.polar_subscription_id, us.current_period_end, us.cancel_at_period_end, us.created_at, us.updated_at
        FROM user_subscriptions us
        JOIN accounts a ON us.user_id = a.owner_user_id
    """))

    # Migrate usage back
    conn.execute(sa.text("""
        INSERT INTO account_usage (account_id, total_queries, total_ingest_requests, total_vectors, last_reset, created_at, updated_at)
        SELECT a.id, uu.total_queries, uu.total_ingest_requests, uu.total_vectors, uu.last_reset, uu.created_at, uu.updated_at
        FROM user_usage uu
        JOIN accounts a ON uu.user_id = a.owner_user_id
    """))

    # Restore projects.account_id
    op.add_column("projects", sa.Column("account_id", sa.Integer(), nullable=True))
    conn.execute(sa.text("""
        UPDATE projects
        SET account_id = accounts.id
        FROM accounts
        WHERE projects.user_id = accounts.owner_user_id
    """))
    op.alter_column("projects", "account_id", nullable=False)
    op.create_foreign_key("projects_account_id_fkey", "projects", "accounts", ["account_id"], ["id"])
    op.drop_constraint(None, "projects", type_="foreignkey")
    op.drop_column("projects", "user_id")

    # Restore rate_limit_buckets.account_id
    op.add_column("rate_limit_buckets", sa.Column("account_id", sa.Integer(), nullable=True))
    conn.execute(sa.text("""
        UPDATE rate_limit_buckets
        SET account_id = accounts.id
        FROM accounts
        WHERE rate_limit_buckets.user_id = accounts.owner_user_id
    """))
    op.alter_column("rate_limit_buckets", "account_id", nullable=False)
    op.drop_constraint("uq_rate_limit_user_type", "rate_limit_buckets", type_="unique")
    op.create_unique_constraint("uq_rate_limit_account_type", "rate_limit_buckets", ["account_id", "limit_type"])
    op.create_foreign_key("rate_limit_buckets_account_id_fkey", "rate_limit_buckets", "accounts", ["account_id"], ["id"])
    op.drop_constraint(None, "rate_limit_buckets", type_="foreignkey")
    op.drop_column("rate_limit_buckets", "user_id")

    # Restore vector_top_ups.account_id if table exists
    table_exists = conn.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'vector_top_ups')")
    ).scalar()

    if table_exists:
        op.add_column("vector_top_ups", sa.Column("account_id", sa.Integer(), nullable=True))
        conn.execute(sa.text("""
            UPDATE vector_top_ups
            SET account_id = accounts.id
            FROM accounts
            WHERE vector_top_ups.user_id = accounts.owner_user_id
        """))
        op.alter_column("vector_top_ups", "account_id", nullable=False)
        op.create_foreign_key("vector_top_ups_account_id_fkey", "vector_top_ups", "accounts", ["account_id"], ["id"])
        op.drop_constraint(None, "vector_top_ups", type_="foreignkey")
        op.drop_column("vector_top_ups", "user_id")

    # Drop new tables
    op.drop_table("user_usage")
    op.drop_table("user_subscriptions")

    # Drop name column from users
    op.drop_column("users", "name")
