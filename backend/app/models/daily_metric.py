"""
Daily Metric Model
Stores daily performance metrics for eBay listings
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, Integer, Date, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class DailyMetric(Base):
    """
    Daily Metric Model
    Stores daily snapshots of listing performance metrics (views, watches, bids, price)
    """
    __tablename__ = "daily_metrics"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Date of the metric snapshot
    recorded_date = Column(Date, nullable=False, index=True)

    # Performance Metrics
    view_count = Column(Integer, default=0, nullable=False)
    watch_count = Column(Integer, default=0, nullable=False)
    bid_count = Column(Integer, default=0, nullable=False)

    # Price at the time of recording
    current_price = Column(Numeric(12, 2), nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    listing = relationship("Listing", back_populates="daily_metrics")

    # Indexes for performance
    __table_args__ = (
        # Unique constraint: one metric per listing per date
        Index('ix_daily_metrics_listing_date', 'listing_id', 'recorded_date', unique=True),
        # Index for date range queries
        Index('ix_daily_metrics_date', 'recorded_date'),
    )

    def __repr__(self):
        return (
            f"<DailyMetric(listing_id={self.listing_id}, "
            f"date={self.recorded_date}, views={self.view_count}, watches={self.watch_count})>"
        )
