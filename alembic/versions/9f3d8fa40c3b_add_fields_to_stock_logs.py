"""Add extra fields to stock_logs

Revision ID: 9f3d8fa40c3b
Revises: 7e1c4d1aa8f0
Create Date: 2024-06-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9f3d8fa40c3b"
down_revision = "7e1c4d1aa8f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stock_logs", sa.Column("marka", sa.String(length=150), nullable=True))
    op.add_column("stock_logs", sa.Column("model", sa.String(length=150), nullable=True))
    op.add_column("stock_logs", sa.Column("lisans_anahtari", sa.String(length=500), nullable=True))
    op.add_column("stock_logs", sa.Column("mail_adresi", sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column("stock_logs", "marka")
    op.drop_column("stock_logs", "model")
    op.drop_column("stock_logs", "lisans_anahtari")
    op.drop_column("stock_logs", "mail_adresi")
