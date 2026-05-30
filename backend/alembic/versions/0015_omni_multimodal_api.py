"""omni multimodal rag api cutover"""

from alembic import op
import sqlalchemy as sa


revision = "0015_omni_multimodal_api"
down_revision = "0014_remote_embeddings"
branch_labels = None
depends_on = None


OMNI_MODEL = "jinaai/jina-embeddings-v5-omni-small-retrieval"


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
        ).bindparams(model=OMNI_MODEL)
    )


def downgrade() -> None:
    pass
