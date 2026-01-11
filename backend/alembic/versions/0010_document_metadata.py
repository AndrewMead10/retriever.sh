"""add metadata to project documents and drop url/published_at"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0010_document_metadata"
down_revision = "0009_project_uuid_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_documents",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute("UPDATE project_documents SET metadata = jsonb_build_object('url', url)")
    op.drop_column("project_documents", "url")
    op.drop_column("project_documents", "published_at")


def downgrade() -> None:
    op.add_column(
        "project_documents",
        sa.Column("published_at", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "project_documents",
        sa.Column("url", sa.String(), nullable=False, server_default=""),
    )
    op.drop_column("project_documents", "metadata")
