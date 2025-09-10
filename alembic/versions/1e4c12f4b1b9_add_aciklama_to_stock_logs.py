"""add aciklama to stock_logs

Revision ID: 1e4c12f4b1b9
Revises: 9f3d8fa40c3b
Create Date: 2025-02-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1e4c12f4b1b9"
down_revision = "9f3d8fa40c3b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stock_logs", sa.Column("aciklama", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("stock_logs", "aciklama")
