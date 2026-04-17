"""add connected accounts and oauth state

Revision ID: 5b4f87dd0b9c
Revises: 4f7d2c10c8a8
Create Date: 2026-04-17 17:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5b4f87dd0b9c"
down_revision = "4f7d2c10c8a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connected_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=True),
        sa.Column("account_type", sa.String(length=100), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_type", sa.String(length=50), nullable=True),
        sa.Column("scopes", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "connection_status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("provider_metadata_json", sa.Text(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "connection_status IN ("
            "'active', "
            "'disconnected', "
            "'reauthorization_required'"
            ")",
            name=op.f("ck_connected_accounts_connection_status_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_connected_accounts")),
        sa.UniqueConstraint(
            "provider_slug",
            name="uq_connected_accounts_provider_slug",
        ),
    )
    op.create_table(
        "oauth_connection_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("state_token", sa.String(length=255), nullable=False),
        sa.Column("code_verifier", sa.Text(), nullable=True),
        sa.Column("pending_payload_json", sa.Text(), nullable=True),
        sa.Column("redirect_after", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_connection_attempts")),
        sa.UniqueConstraint(
            "state_token",
            name="uq_oauth_connection_attempts_state_token",
        ),
    )

    with op.batch_alter_table("post_platform_logs") as batch_op:
        batch_op.add_column(sa.Column("account_display_name", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("account_identifier", sa.Text(), nullable=True))
        batch_op.drop_constraint("status_allowed", type_="check")
        batch_op.create_check_constraint(
            "status_allowed",
            "status IN ("
            "'pending', "
            "'posted', "
            "'not_configured', "
            "'not_connected', "
            "'reauthorization_required', "
            "'unsupported', "
            "'validation_failed', "
            "'submission_failed'"
            ")",
        )


def downgrade() -> None:
    with op.batch_alter_table("post_platform_logs") as batch_op:
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
        batch_op.drop_column("account_identifier")
        batch_op.drop_column("account_display_name")

    op.drop_table("oauth_connection_attempts")
    op.drop_table("connected_accounts")
