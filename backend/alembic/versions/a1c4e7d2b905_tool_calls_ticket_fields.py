"""tool calls, ticket fields, directory username

Brings the tables in line with the models from PRs #28-#30: tickets get the
create_ticket fields (ticket number, category, affected system, club, Jira sync),
users get the mock-directory username for reset_password, and tool_calls is new.

Existing ticket rows are kept: user_id/subject are renamed, new required columns
get a default for old rows.

Revision ID: a1c4e7d2b905
Revises: febefce2c3ea
Create Date: 2026-11-17 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1c4e7d2b905"
down_revision: str | Sequence[str] | None = "febefce2c3ea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tickets") as t:
        t.alter_column("user_id", new_column_name="requester_id")
        t.alter_column(
            "subject",
            new_column_name="summary",
            type_=sa.String(length=120),
            existing_type=sa.String(length=200),
            existing_nullable=False,
        )
        t.alter_column(
            "priority",
            type_=sa.String(length=10),
            existing_type=sa.String(length=30),
            existing_nullable=False,
        )
        t.add_column(sa.Column("ticket_number", sa.String(length=20), nullable=True))
        t.add_column(
            sa.Column("category", sa.String(length=40), nullable=False, server_default="other")
        )
        t.add_column(
            sa.Column(
                "affected_system", sa.String(length=40), nullable=False, server_default="other"
            )
        )
        t.add_column(sa.Column("club_code", sa.String(length=10), nullable=True))
        t.add_column(sa.Column("jira_key", sa.String(length=30), nullable=True))
        t.add_column(
            sa.Column(
                "jira_sync_status", sa.String(length=20), nullable=False, server_default="pending"
            )
        )
        t.create_unique_constraint("uq_tickets_ticket_number", ["ticket_number"])

    # Old rows got their defaults; new rows always set these in code.
    with op.batch_alter_table("tickets") as t:
        t.alter_column("category", server_default=None)
        t.alter_column("affected_system", server_default=None)
        t.alter_column("jira_sync_status", server_default=None)

    with op.batch_alter_table("users") as t:
        t.add_column(sa.Column("directory_username", sa.String(length=60), nullable=True))
        t.create_unique_constraint("uq_users_directory_username", ["directory_username"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("tool_calls")

    with op.batch_alter_table("users") as t:
        t.drop_constraint("uq_users_directory_username", type_="unique")
        t.drop_column("directory_username")

    with op.batch_alter_table("tickets") as t:
        t.drop_constraint("uq_tickets_ticket_number", type_="unique")
        for name in (
            "jira_sync_status",
            "jira_key",
            "club_code",
            "affected_system",
            "category",
            "ticket_number",
        ):
            t.drop_column(name)
        t.alter_column(
            "priority",
            type_=sa.String(length=30),
            existing_type=sa.String(length=10),
            existing_nullable=False,
        )
        t.alter_column(
            "summary",
            new_column_name="subject",
            type_=sa.String(length=200),
            existing_type=sa.String(length=120),
            existing_nullable=False,
        )
        t.alter_column("requester_id", new_column_name="user_id")
