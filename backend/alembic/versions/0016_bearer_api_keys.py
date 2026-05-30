"""bearer api keys and management keys"""

from alembic import op
import sqlalchemy as sa


revision = "0016_bearer_api_keys"
down_revision = "0015_omni_multimodal_api"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_api_keys", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.add_column("project_api_keys", sa.Column("revoked_at", sa.DateTime(), nullable=True))

    op.execute(
        sa.text(
            """
            INSERT INTO project_api_keys (
                project_id,
                name,
                prefix,
                hashed_key,
                last_used_at,
                expires_at,
                revoked,
                revoked_at,
                created_at,
                updated_at
            )
            SELECT
                p.id,
                'Legacy project key',
                'proj_legacy',
                p.ingest_api_key_hash,
                NULL,
                NULL,
                false,
                NULL,
                now(),
                now()
            FROM projects p
            WHERE p.ingest_api_key_hash IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM project_api_keys pak
                  WHERE pak.project_id = p.id
                    AND pak.hashed_key = p.ingest_api_key_hash
              )
            """
        )
    )

    op.drop_column("projects", "ingest_api_key_hash")

    op.create_table(
        "management_api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("prefix", sa.String(), nullable=False),
        sa.Column("hashed_key", sa.String(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hashed_key"),
    )
    op.create_index(
        op.f("ix_management_api_keys_user_id"),
        "management_api_keys",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_management_api_keys_created_at"),
        "management_api_keys",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "api_key_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key_type", sa.String(), nullable=False),
        sa.Column("key_prefix", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_api_key_audit_events_user_id"),
        "api_key_audit_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_api_key_audit_events_created_at"),
        "api_key_audit_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("ingest_api_key_hash", sa.String(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE projects p
            SET ingest_api_key_hash = key_row.hashed_key
            FROM (
                SELECT DISTINCT ON (project_id)
                    project_id,
                    hashed_key
                FROM project_api_keys
                WHERE revoked = false
                ORDER BY project_id, created_at DESC
            ) AS key_row
            WHERE key_row.project_id = p.id
            """
        )
    )
    op.alter_column("projects", "ingest_api_key_hash", nullable=False)
    op.drop_index(op.f("ix_api_key_audit_events_created_at"), table_name="api_key_audit_events")
    op.drop_index(op.f("ix_api_key_audit_events_user_id"), table_name="api_key_audit_events")
    op.drop_table("api_key_audit_events")
    op.drop_index(op.f("ix_management_api_keys_created_at"), table_name="management_api_keys")
    op.drop_index(op.f("ix_management_api_keys_user_id"), table_name="management_api_keys")
    op.drop_table("management_api_keys")
    op.drop_column("project_api_keys", "revoked_at")
    op.drop_column("project_api_keys", "expires_at")
