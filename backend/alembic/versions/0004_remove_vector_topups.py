"""remove vector top-ups

Revision ID: 0004_remove_vector_topups
Revises: 0003_replace_stripe_with_polar
Create Date: 2025-11-09 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_remove_vector_topups"
down_revision = "0003_replace_stripe_with_polar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_vector_top_ups_account_id", table_name="vector_top_ups")
    op.drop_table("vector_top_ups")

    with op.batch_alter_table("plans") as batch_op:
        batch_op.drop_column("allow_topups")


def downgrade() -> None:
    with op.batch_alter_table("plans") as batch_op:
        batch_op.add_column(
            sa.Column(
                "allow_topups",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("FALSE"),
            )
        )

    op.create_table(
        "vector_top_ups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("vectors_granted", sa.Integer(), nullable=False),
        sa.Column("vectors_remaining", sa.Integer(), nullable=False),
        sa.Column("polar_order_id", sa.String(), nullable=True),
        sa.Column("purchased_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_vector_top_ups_account_id", "vector_top_ups", ["account_id"])
