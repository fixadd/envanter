"""Drop unused stock_transactions table

Revision ID: e6c1d9b8f4d1
Revises: 1e4c12f4b1b9
Create Date: 2025-02-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e6c1d9b8f4d1"
down_revision = "1e4c12f4b1b9"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "stock_transactions" in inspector.get_table_names():
        op.drop_table("stock_transactions")


def downgrade():
    op.create_table(
        "stock_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("donanim_tipi", sa.String(length=120), nullable=False),
        sa.Column("islem", sa.String(length=16), nullable=False),
        sa.Column("miktar", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ifs_no", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_stock_transactions_donanim_tipi",
        "stock_transactions",
        ["donanim_tipi"],
    )
