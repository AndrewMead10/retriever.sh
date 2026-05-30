"""multimodal rag api cutover"""

from alembic import op
import sqlalchemy as sa


revision = "0015_multimodal_rag_api"
down_revision = "0014_remote_embeddings"
branch_labels = None
depends_on = None


EMBEDDING_MODEL = "jinaai/jina-embeddings-v5-text-small-retrieval-mlx"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE projects
            SET embedding_provider = 'remote-http',
                embedding_model = :model,
                embedding_model_repo = NULL,
                embedding_model_file = NULL,
                embedding_dim = 512
            """
        ).bindparams(model=EMBEDDING_MODEL)
    )


def downgrade() -> None:
    pass
