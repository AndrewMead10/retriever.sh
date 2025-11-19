"""Switch vector store identifiers for PostgreSQL-backed hybrid search."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_postgres_vector_store"
down_revision = "0003_replace_stripe_with_polar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    conn = op.get_bind()
    projects = conn.execute(sa.text("SELECT id FROM projects")).fetchall()
    for row in projects:
        table_name = f"rag_documents_proj_{row.id}"
        conn.execute(
            sa.text("UPDATE projects SET vector_store_path = :table_name WHERE id = :project_id"),
            {"table_name": table_name, "project_id": row.id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE projects SET vector_store_path = CONCAT('legacy_', vector_store_path)")
    )
