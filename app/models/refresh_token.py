"""
Refresh Token model for JWT token rotation and security.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RefreshToken(Base):
    """
    Refresh Token model for storing and managing JWT refresh tokens.

    Supports:
    - Token rotation on refresh
    - Token revocation (logout)
    - Maximum tokens per user (auto-cleanup)
    - Device tracking
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Store hashed token (never store plain tokens)
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    revoked_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Device tracking for security
    device_info: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    ip_address: Mapped[str] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # Relationship to user
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    # Indexes for query optimization
    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_token", "token"),
        Index("idx_refresh_tokens_expires_at", "expires_at"),
        Index("idx_refresh_tokens_user_expires", "user_id", "expires_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<RefreshToken(id={self.id}, user_id={self.user_id}, "
            f"expires_at={self.expires_at}, revoked={self.revoked_at is not None})>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked
