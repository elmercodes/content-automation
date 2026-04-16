"""Core ORM models for master posts, media items, and post platform logs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

MEDIA_TYPES = ("image", "video")
POST_PLATFORM_LOG_STATUSES = ("pending", "posted", "failed")


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
            "status IN ('pending', 'posted', 'failed')",
            name="status_allowed",
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
    error_message: Mapped[str | None] = mapped_column(Text)

    post: Mapped[Post] = relationship(back_populates="post_platform_logs")
