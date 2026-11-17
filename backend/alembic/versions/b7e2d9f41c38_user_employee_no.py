"""users.employee_no for the reset_password code request

Revision ID: b7e2d9f41c38
Revises: a1c4e7d2b905
Create Date: 2026-11-17 18:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e2d9f41c38"
down_revision: str | Sequence[str] | None = "a1c4e7d2b905"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as t:
        t.add_column(sa.Column("employee_no", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as t:
        t.drop_column("employee_no")
