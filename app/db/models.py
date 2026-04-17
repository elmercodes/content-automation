"""Core ORM models for master posts, media items, connected accounts, and logs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

MEDIA_TYPES = ("image", "video")
POST_PLATFORM_LOG_STATUSES = (
    "pending",
    "posted",
    "not_configured",
    "not_connected",
    "reauthorization_required",
    "unsupported",
    "validation_failed",
    "submission_failed",
)
CONNECTED_ACCOUNT_STATUSES = (
    "active",
    "disconnected",
    "reauthorization_required",
)


def utcnow() -> datetime:
    """Return the current UTC timestamp for ORM-managed defaults."""

    return datetime.now(UTC)


class Post(Base):
    """The master post record that anchors one publishing intent."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    caption: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    hashtags: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    media_items: Mapped[list["MediaItem"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="MediaItem.display_order",
    )
    post_platform_logs: Mapped[list["PostPlatformLog"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostPlatformLog.created_at",
    )


class MediaItem(Base):
    """An ordered media asset attached to a master post."""

    __tablename__ = "media_items"
    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "display_order",
            name="uq_media_items_post_id_display_order",
        ),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
        CheckConstraint(
            "media_type IN ('image', 'video')",
            name="media_type_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    display_order: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    post: Mapped[Post] = relationship(back_populates="media_items")


class PostPlatformLog(Base):
    """A per-platform record of submission intent or outcome."""

    __tablename__ = "post_platform_logs"
    __table_args__ = (
        CheckConstraint(
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
            name="status_allowed",
        ),
        Index(
            "ix_post_platform_logs_post_id_platform_slug_created_at",
            "post_id",
            "platform_slug",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_post_id: Mapped[str | None] = mapped_column(Text)
    account_display_name: Mapped[str | None] = mapped_column(Text)
    account_identifier: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    response_summary: Mapped[str | None] = mapped_column(Text)

    post: Mapped[Post] = relationship(back_populates="post_platform_logs")


class ConnectedAccount(Base):
    """A locally stored provider account authorized through OAuth."""

    __tablename__ = "connected_accounts"
    __table_args__ = (
        UniqueConstraint("provider_slug", name="uq_connected_accounts_provider_slug"),
        CheckConstraint(
            "connection_status IN ("
            "'active', "
            "'disconnected', "
            "'reauthorization_required'"
            ")",
            name="connection_status_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_account_id: Mapped[str | None] = mapped_column(String(255))
    account_type: Mapped[str | None] = mapped_column(String(100))
    display_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_type: Mapped[str | None] = mapped_column(String(50))
    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connection_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    provider_metadata_json: Mapped[str | None] = mapped_column(Text)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class OAuthConnectionAttempt(Base):
    """Short-lived local OAuth state and PKCE verifier storage."""

    __tablename__ = "oauth_connection_attempts"
    __table_args__ = (
        UniqueConstraint(
            "state_token",
            name="uq_oauth_connection_attempts_state_token",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    state_token: Mapped[str] = mapped_column(String(255), nullable=False)
    code_verifier: Mapped[str | None] = mapped_column(Text)
    pending_payload_json: Mapped[str | None] = mapped_column(Text)
    redirect_after: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
