"""add email verification to users

Revision ID: 0004_add_email_verification
Revises: 0003_postgres_vector_store
Create Date: 2025-11-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_add_email_verification"
down_revision = "0003_postgres_vector_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")))
    op.add_column("users", sa.Column("email_verification_token", sa.String(), nullable=True))
    op.add_column("users", sa.Column("email_verification_token_expires_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_email_verification_token", "users", ["email_verification_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email_verification_token", table_name="users")
    op.drop_column("users", "email_verification_token_expires_at")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "is_email_verified")
