"""convert project ids from integer to uuid7

SQLite doesn't support ALTER COLUMN, so we:
1. Create new tables with UUID primary keys
2. Migrate data with generated UUIDv7s
3. Drop old tables
4. Rename new tables
"""

from uuid6 import uuid7
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "0009_project_uuid_ids"
down_revision = "0008_add_project_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create new projects table with UUID primary key
    op.create_table(
        "projects_new",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("embedding_provider", sa.String(), nullable=False),
        sa.Column("embedding_model", sa.String(), nullable=False),
        sa.Column("embedding_model_repo", sa.String(), nullable=True),
        sa.Column("embedding_model_file", sa.String(), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("hybrid_weight_vector", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("hybrid_weight_text", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("top_k_default", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("vector_search_k", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("vector_store_path", sa.String(), nullable=False),
        sa.Column("vector_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ingest_api_key_hash", sa.String(), nullable=False),
        sa.Column("last_ingest_at", sa.DateTime(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )

    # 2. Migrate projects data, generating UUIDs and keeping a mapping
    old_projects = conn.execute(sa.text("SELECT * FROM projects")).fetchall()
    id_mapping = {}  # old_id -> new_uuid

    for row in old_projects:
        new_uuid = str(uuid7())
        id_mapping[row[0]] = new_uuid  # row[0] is the old integer id

        conn.execute(
            sa.text("""
                INSERT INTO projects_new (
                    id, user_id, name, description, slug,
                    embedding_provider, embedding_model, embedding_model_repo, embedding_model_file,
                    embedding_dim, hybrid_weight_vector, hybrid_weight_text,
                    top_k_default, vector_search_k, vector_store_path, vector_count,
                    ingest_api_key_hash, last_ingest_at, active, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :name, :description, :slug,
                    :embedding_provider, :embedding_model, :embedding_model_repo, :embedding_model_file,
                    :embedding_dim, :hybrid_weight_vector, :hybrid_weight_text,
                    :top_k_default, :vector_search_k, :vector_store_path, :vector_count,
                    :ingest_api_key_hash, :last_ingest_at, :active, :created_at, :updated_at
                )
            """),
            {
                "id": new_uuid,
                "user_id": row[1],
                "name": row[2],
                "description": row[3],
                "slug": row[4],
                "embedding_provider": row[5],
                "embedding_model": row[6],
                "embedding_model_repo": row[7],
                "embedding_model_file": row[8],
                "embedding_dim": row[9],
                "hybrid_weight_vector": row[10],
                "hybrid_weight_text": row[11],
                "top_k_default": row[12],
                "vector_search_k": row[13],
                "vector_store_path": row[14],
                "vector_count": row[15],
                "ingest_api_key_hash": row[16],
                "last_ingest_at": row[17],
                "active": row[18],
                "created_at": row[19],
                "updated_at": row[20],
            },
        )

    # 3. Create new project_api_keys table with String FK
    op.create_table(
        "project_api_keys_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects_new.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("prefix", sa.String(), nullable=False),
        sa.Column("hashed_key", sa.String(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )

    # Migrate project_api_keys data with new project UUIDs
    old_api_keys = conn.execute(sa.text("SELECT * FROM project_api_keys")).fetchall()
    for row in old_api_keys:
        old_project_id = row[1]
        if old_project_id in id_mapping:
            conn.execute(
                sa.text("""
                    INSERT INTO project_api_keys_new (
                        id, project_id, name, prefix, hashed_key,
                        last_used_at, revoked, created_at, updated_at
                    ) VALUES (
                        :id, :project_id, :name, :prefix, :hashed_key,
                        :last_used_at, :revoked, :created_at, :updated_at
                    )
                """),
                {
                    "id": row[0],
                    "project_id": id_mapping[old_project_id],
                    "name": row[2],
                    "prefix": row[3],
                    "hashed_key": row[4],
                    "last_used_at": row[5],
                    "revoked": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                },
            )

    # 4. Create new project_documents table with String FK
    op.create_table(
        "project_documents_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects_new.id"), nullable=False, index=True),
        sa.Column("vespa_document_id", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("published_at", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=func.now()),
    )

    # Migrate project_documents data with new project UUIDs
    old_documents = conn.execute(sa.text("SELECT * FROM project_documents")).fetchall()
    for row in old_documents:
        old_project_id = row[1]
        if old_project_id in id_mapping:
            conn.execute(
                sa.text("""
                    INSERT INTO project_documents_new (
                        id, project_id, vespa_document_id, title, content,
                        url, published_at, active, created_at, updated_at
                    ) VALUES (
                        :id, :project_id, :vespa_document_id, :title, :content,
                        :url, :published_at, :active, :created_at, :updated_at
                    )
                """),
                {
                    "id": row[0],
                    "project_id": id_mapping[old_project_id],
                    "vespa_document_id": row[2],
                    "title": row[3],
                    "content": row[4],
                    "url": row[5],
                    "published_at": row[6],
                    "active": row[7],
                    "created_at": row[8],
                    "updated_at": row[9],
                },
            )

    # 5. Drop old tables and rename new ones
    op.drop_table("project_documents")
    op.drop_table("project_api_keys")
    op.drop_table("projects")

    op.rename_table("projects_new", "projects")
    op.rename_table("project_api_keys_new", "project_api_keys")
    op.rename_table("project_documents_new", "project_documents")


def downgrade() -> None:
    # This migration is not reversible without data loss
    # You'd need to convert UUIDs back to sequential integers
    raise NotImplementedError("Downgrade not supported for UUID migration")
