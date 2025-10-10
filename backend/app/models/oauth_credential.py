"""
OAuth Credential Model
"""
from sqlalchemy import Column, String, DateTime, Boolean, ARRAY, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class OAuthCredential(Base):
    """
    OAuth Credential model - stores encrypted eBay OAuth tokens

    Tokens are encrypted using AES-256-GCM before storage.
    Each tenant can have only one OAuth credential (enforced by unique constraint).
    """
    __tablename__ = "oauth_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One OAuth credential per tenant
        index=True
    )

    # Encrypted access token (AES-256-GCM)
    access_token_encrypted = Column(LargeBinary, nullable=False)
    access_token_iv = Column(LargeBinary, nullable=False)  # Initialization vector
    access_token_auth_tag = Column(LargeBinary, nullable=False)  # Authentication tag

    # Encrypted refresh token (AES-256-GCM)
    refresh_token_encrypted = Column(LargeBinary, nullable=False)
    refresh_token_iv = Column(LargeBinary, nullable=False)
    refresh_token_auth_tag = Column(LargeBinary, nullable=False)

    # Token metadata
    access_token_expires_at = Column(DateTime, nullable=False)
    refresh_token_expires_at = Column(DateTime, nullable=True)  # Some tokens don't expire
    scopes = Column(ARRAY(String), nullable=False)  # OAuth scopes granted

    # Status
    is_valid = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="oauth_credential")
    ebay_accounts = relationship("EbayAccount", back_populates="oauth_credential", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OAuthCredential(id={self.id}, tenant_id={self.tenant_id}, is_valid={self.is_valid})>"

    def to_dict(self):
        """Convert to dictionary (excluding sensitive encrypted data)"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "access_token_expires_at": self.access_token_expires_at.isoformat() if self.access_token_expires_at else None,
            "refresh_token_expires_at": self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None,
            "scopes": self.scopes,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_access_token_expired(self) -> bool:
        """Check if access token is expired"""
        if not self.access_token_expires_at:
            return True
        return datetime.utcnow() >= self.access_token_expires_at

    def is_refresh_token_expired(self) -> bool:
        """Check if refresh token is expired"""
        if not self.refresh_token_expires_at:
            return False  # No expiration
        return datetime.utcnow() >= self.refresh_token_expires_at
