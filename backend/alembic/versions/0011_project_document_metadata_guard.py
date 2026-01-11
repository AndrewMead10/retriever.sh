"""ensure metadata column exists on project_documents"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0011_project_document_metadata_guard"
down_revision = "0010_document_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE project_documents "
        "ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb"
    )
    op.execute("ALTER TABLE project_documents DROP COLUMN IF EXISTS url")
    op.execute("ALTER TABLE project_documents DROP COLUMN IF EXISTS published_at")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE project_documents "
        "ADD COLUMN IF NOT EXISTS url varchar NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE project_documents "
        "ADD COLUMN IF NOT EXISTS published_at varchar NOT NULL DEFAULT ''"
    )
    op.execute("ALTER TABLE project_documents DROP COLUMN IF EXISTS metadata")
