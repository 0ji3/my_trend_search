"""
Listing Model
Stores eBay listing/item information
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Listing(Base):
    """
    eBay Listing Model
    Stores active and historical listings from eBay seller accounts
    """
    __tablename__ = "listings"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ebay_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # eBay Item Information
    item_id = Column(String(50), nullable=False, index=True)  # eBay Item ID
    title = Column(Text, nullable=False)
    price = Column(Numeric(12, 2), nullable=True)  # Current price
    currency = Column(String(3), default="USD", nullable=False)

    # Category Information
    category_id = Column(String(50), nullable=True, index=True)
    category_name = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Media
    image_url = Column(Text, nullable=True)

    # Item Specifics (flexible JSON storage for custom attributes)
    item_specifics = Column(JSONB, nullable=True)

    # Listing Type and Status
    listing_type = Column(String(50), nullable=True)  # FixedPriceItem, Auction, etc.
    listing_status = Column(String(50), nullable=True)  # Active, Completed, Ended

    # Quantity Information
    quantity = Column(Integer, default=1, nullable=True)
    quantity_sold = Column(Integer, default=0, nullable=True)

    # Timestamps
    start_time = Column(DateTime, nullable=True)  # Listing start time
    end_time = Column(DateTime, nullable=True)    # Listing end time
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    account = relationship("EbayAccount", back_populates="listings")
    daily_metrics = relationship(
        "DailyMetric",
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="DailyMetric.recorded_date.desc()"
    )
    trend_analyses = relationship(
        "TrendAnalysis",
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="TrendAnalysis.analysis_date.desc()"
    )

    # Indexes for performance
    __table_args__ = (
        # Unique constraint: one item_id per account
        Index('ix_listings_account_item', 'account_id', 'item_id', unique=True),
        # Composite index for querying active listings by account
        Index('ix_listings_account_active', 'account_id', 'is_active'),
    )

    def __repr__(self):
        return f"<Listing(id={self.id}, item_id={self.item_id}, title={self.title[:30]})>"
