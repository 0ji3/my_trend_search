"""
eBay Account Model
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class EbayAccount(Base):
    """
    eBay Account model - represents a connected eBay seller account

    Each OAuth credential can have multiple eBay accounts (multi-user grant).
    Each account can have multiple listings.
    """
    __tablename__ = "ebay_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oauth_credential_id = Column(
        UUID(as_uuid=True),
        ForeignKey("oauth_credentials.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # eBay account information
    ebay_user_id = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    marketplace_id = Column(String(50), default="EBAY_US")  # EBAY_US, EBAY_UK, etc.

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)  # Last successful data sync

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="ebay_accounts")
    oauth_credential = relationship("OAuthCredential", back_populates="ebay_accounts")
    listings = relationship("Listing", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EbayAccount(id={self.id}, ebay_user_id={self.ebay_user_id}, username={self.username})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "oauth_credential_id": str(self.oauth_credential_id),
            "ebay_user_id": self.ebay_user_id,
            "username": self.username,
            "email": self.email,
            "marketplace_id": self.marketplace_id,
            "is_active": self.is_active,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
