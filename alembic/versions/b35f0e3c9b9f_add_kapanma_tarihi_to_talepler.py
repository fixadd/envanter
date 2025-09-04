"""Add kapanma_tarihi to talepler

Revision ID: b35f0e3c9b9f
Revises: c8b2f8041a88
Create Date: 2024-11-09
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b35f0e3c9b9f"
down_revision = "c8b2f8041a88"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("talepler", sa.Column("kapanma_tarihi", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("talepler", "kapanma_tarihi")
