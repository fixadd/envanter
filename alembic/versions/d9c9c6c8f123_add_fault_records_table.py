"""add fault records table

Revision ID: d9c9c6c8f123
Revises: 1e4c12f4b1b9
Create Date: 2025-03-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d9c9c6c8f123"
down_revision = "1e4c12f4b1b9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fault_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity_key", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("device_no", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("destination", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="arızalı"),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("resolved_by", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("meta", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_fault_records_entity_type",
        "fault_records",
        ["entity_type"],
    )
    op.create_index(
        "ix_fault_records_entity_id",
        "fault_records",
        ["entity_id"],
    )
    op.create_index(
        "ix_fault_records_entity_key",
        "fault_records",
        ["entity_key"],
    )
    op.create_index("ix_fault_records_status", "fault_records", ["status"])


def downgrade():
    op.drop_index("ix_fault_records_status", table_name="fault_records")
    op.drop_index("ix_fault_records_entity_key", table_name="fault_records")
    op.drop_index("ix_fault_records_entity_id", table_name="fault_records")
    op.drop_index("ix_fault_records_entity_type", table_name="fault_records")
    op.drop_table("fault_records")
