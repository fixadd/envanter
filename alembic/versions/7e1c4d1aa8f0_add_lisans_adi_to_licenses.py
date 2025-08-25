"""Add lisans_adi column to licenses

Revision ID: 7e1c4d1aa8f0
Revises: None
Create Date: 2024-05-30
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7e1c4d1aa8f0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("licenses", sa.Column("lisans_adi", sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column("licenses", "lisans_adi")

