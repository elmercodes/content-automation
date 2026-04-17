"""expand post platform log statuses for posting

Revision ID: 4f7d2c10c8a8
Revises: 2d8d42ce9fad
Create Date: 2026-04-17 12:15:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4f7d2c10c8a8"
down_revision = "2d8d42ce9fad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("post_platform_logs") as batch_op:
        batch_op.add_column(sa.Column("response_summary", sa.Text(), nullable=True))
        batch_op.drop_constraint("status_allowed", type_="check")
        batch_op.create_check_constraint(
            "status_allowed",
            "status IN ("
            "'pending', "
            "'posted', "
            "'not_configured', "
            "'unsupported', "
            "'validation_failed', "
            "'submission_failed'"
            ")",
        )

    op.create_index(
        "ix_post_platform_logs_post_id_platform_slug_created_at",
        "post_platform_logs",
        ["post_id", "platform_slug", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_post_platform_logs_post_id_platform_slug_created_at",
        table_name="post_platform_logs",
    )

    with op.batch_alter_table("post_platform_logs") as batch_op:
        batch_op.drop_constraint("status_allowed", type_="check")
        batch_op.create_check_constraint(
            "status_allowed",
            "status IN ('pending', 'posted', 'failed')",
        )
        batch_op.drop_column("response_summary")
