"""create products table

Revision ID: 2d7a2f6f1c3e
Revises: 1e4c12f4b1b9
Create Date: 2025-03-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2d7a2f6f1c3e"
down_revision = "1e4c12f4b1b9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("donanim_tipi", sa.String(length=100), nullable=False),
        sa.Column("marka", sa.String(length=150), nullable=True),
        sa.Column("model", sa.String(length=150), nullable=True),
        sa.Column("kullanim_alani", sa.String(length=150), nullable=True),
        sa.Column("lisans_adi", sa.String(length=150), nullable=True),
        sa.Column("fabrika", sa.String(length=150), nullable=True),
    )
    op.create_index("ix_products_donanim_tipi", "products", ["donanim_tipi"])
    op.create_index("ix_products_marka", "products", ["marka"])
    op.create_index("ix_products_model", "products", ["model"])
    op.create_index("ix_products_kullanim_alani", "products", ["kullanim_alani"])
    op.create_index("ix_products_fabrika", "products", ["fabrika"])


def downgrade():
    op.drop_index("ix_products_fabrika", table_name="products")
    op.drop_index("ix_products_kullanim_alani", table_name="products")
    op.drop_index("ix_products_model", table_name="products")
    op.drop_index("ix_products_marka", table_name="products")
    op.drop_index("ix_products_donanim_tipi", table_name="products")
    op.drop_table("products")
