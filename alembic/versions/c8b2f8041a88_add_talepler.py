"""add talepler table

Revision ID: c8b2f8041a88
Revises: 9f3d8fa40c3b
Create Date: 2024-10-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c8b2f8041a88"
down_revision = "9f3d8fa40c3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "talepler",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tur",
            sa.Enum("envanter", "lisans", "aksesuar", name="talepturu"),
            nullable=False,
        ),
        sa.Column("ifs_no", sa.String(100), nullable=True),
        sa.Column("miktar", sa.Integer(), nullable=True),
        sa.Column("marka", sa.String(150), nullable=True),
        sa.Column("model", sa.String(150), nullable=True),
        sa.Column("envanter_no", sa.String(100), nullable=True),
        sa.Column("sorumlu_personel", sa.String(150), nullable=True),
        sa.Column("bagli_envanter_no", sa.String(100), nullable=True),
        sa.Column("lisans_adi", sa.String(200), nullable=True),
        sa.Column("aciklama", sa.Text(), nullable=True),
        sa.Column(
            "durum",
            sa.Enum("aktif", "kapali", "iptal", name="talepdurum"),
            nullable=False,
            server_default="aktif",
        ),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_talepler_ifs_no", "talepler", ["ifs_no"])


def downgrade() -> None:
    op.drop_index("ix_talepler_ifs_no", table_name="talepler")
    op.drop_table("talepler")
    op.execute("DROP TYPE IF EXISTS talepturu")
    op.execute("DROP TYPE IF EXISTS talepdurum")

