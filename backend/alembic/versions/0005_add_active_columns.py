"""add active columns to projects and vector tables

Revision ID: 0005_add_active_columns
Revises: 0004_remove_vector_topups
Create Date: 2025-11-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_add_active_columns"
down_revision = "0004_remove_vector_topups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add active column to projects table
    op.add_column("projects", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")))

    # Add active column to all existing vector tables
    conn = op.get_bind()
    projects = conn.execute(sa.text("SELECT id, vector_store_path FROM projects")).fetchall()

    for row in projects:
        table_name = row.vector_store_path
        if table_name:
            # Check if table exists before trying to alter it
            table_exists = conn.execute(
                sa.text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
                ),
                {"table_name": table_name}
            ).scalar()

            if table_exists:
                conn.execute(
                    sa.text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS active INTEGER NOT NULL DEFAULT 1")
                )


def downgrade() -> None:
    # Remove active column from all vector tables
    conn = op.get_bind()
    projects = conn.execute(sa.text("SELECT id, vector_store_path FROM projects")).fetchall()

    for row in projects:
        table_name = row.vector_store_path
        if table_name:
            table_exists = conn.execute(
                sa.text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
                ),
                {"table_name": table_name}
            ).scalar()

            if table_exists:
                conn.execute(
                    sa.text(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS active")
                )

    # Remove active column from projects table
    op.drop_column("projects", "active")
