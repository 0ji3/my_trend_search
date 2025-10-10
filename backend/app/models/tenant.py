"""
Tenant (User) Model
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class TenantStatus(str, enum.Enum):
    """Tenant status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Tenant(Base):
    """
    Tenant model - represents a user account

    This is the main user table for multi-tenant support.
    Each tenant can have multiple eBay accounts connected.
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=True)
    timezone = Column(String(50), default="UTC")
    status = Column(
        String(20),  # Use String instead of Enum to avoid SQLAlchemy enum issues
        default="active",
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tenant(id={self.id}, email={self.email}, status={self.status})>"

    def to_dict(self):
        """Convert to dictionary (excluding password)"""
        return {
            "id": str(self.id),
            "email": self.email,
            "business_name": self.business_name,
            "timezone": self.timezone,
            "status": self.status.value if isinstance(self.status, TenantStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
