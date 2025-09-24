"""create system_room_items table

Revision ID: 5cf4d4b998eb
Revises: d9c9c6c8f123
Create Date: 2025-03-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5cf4d4b998eb"
down_revision = "d9c9c6c8f123"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "system_room_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("donanim_tipi", sa.String(length=150), nullable=False),
        sa.Column("marka", sa.String(length=150), nullable=True),
        sa.Column("model", sa.String(length=150), nullable=True),
        sa.Column("ifs_no", sa.String(length=100), nullable=True),
        sa.Column(
            "assigned_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("assigned_by", sa.String(length=150), nullable=True),
        sa.UniqueConstraint(
            "item_type",
            "donanim_tipi",
            "marka",
            "model",
            "ifs_no",
            name="uq_system_room_key",
        ),
    )


def downgrade():
    op.drop_table("system_room_items")
