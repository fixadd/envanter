"""add license metadata columns

Revision ID: f8b1234d9abc
Revises: e6c1d9b8f4d1
Create Date: 2025-02-20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f8b1234d9abc"
down_revision = "e6c1d9b8f4d1"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    if not _table_exists(bind, "departments"):
        op.create_table(
            "departments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=150), nullable=False, unique=True),
        )
        op.create_index("ix_departments_name", "departments", ["name"], unique=True)

    op.add_column("licenses", sa.Column("license_code", sa.String(length=64), nullable=True))
    op.add_column("licenses", sa.Column("license_type", sa.String(length=32), nullable=True))
    op.add_column(
        "licenses",
        sa.Column("seat_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("licenses", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("licenses", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("licenses", sa.Column("factory_id", sa.Integer(), nullable=True))
    op.add_column("licenses", sa.Column("department_id", sa.Integer(), nullable=True))
    op.add_column("licenses", sa.Column("owner_id", sa.Integer(), nullable=True))

    op.create_index("ix_licenses_license_code", "licenses", ["license_code"], unique=True)

    op.create_foreign_key(
        "fk_licenses_factory_id_factories",
        "licenses",
        "factories",
        ["factory_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_licenses_department_id_departments",
        "licenses",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_licenses_owner_id_users",
        "licenses",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "licenses",
        "seat_count",
        server_default=None,
        existing_type=sa.Integer(),
    )


def downgrade():
    op.drop_constraint("fk_licenses_owner_id_users", "licenses", type_="foreignkey")
    op.drop_constraint(
        "fk_licenses_department_id_departments", "licenses", type_="foreignkey"
    )
    op.drop_constraint("fk_licenses_factory_id_factories", "licenses", type_="foreignkey")
    op.drop_index("ix_licenses_license_code", table_name="licenses")

    op.drop_column("licenses", "owner_id")
    op.drop_column("licenses", "department_id")
    op.drop_column("licenses", "factory_id")
    op.drop_column("licenses", "end_date")
    op.drop_column("licenses", "start_date")
    op.drop_column("licenses", "seat_count")
    op.drop_column("licenses", "license_type")
    op.drop_column("licenses", "license_code")

    bind = op.get_bind()
    if _table_exists(bind, "departments"):
        op.drop_index("ix_departments_name", table_name="departments")
        op.drop_table("departments")
