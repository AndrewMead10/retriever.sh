"""add project_images table for multimodal retrieval"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0012_add_project_images"
down_revision = "0011_doc_metadata_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("vespa_document_id", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint("vespa_document_id"),
    )
    op.create_index(op.f("ix_project_images_created_at"), "project_images", ["created_at"], unique=False)
    op.create_index(op.f("ix_project_images_project_id"), "project_images", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_images_project_id"), table_name="project_images")
    op.drop_index(op.f("ix_project_images_created_at"), table_name="project_images")
    op.drop_table("project_images")
