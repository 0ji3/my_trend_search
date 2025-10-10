"""
Analytics Metric Model

Analytics APIから取得した詳細メトリクスを保存
"""
from sqlalchemy import Column, String, Integer, Numeric, Date, DateTime, ForeignKey, UUID, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class AnalyticsMetric(Base):
    """
    Analytics APIメトリクスモデル

    eBay Analytics APIから取得した詳細なトラフィックデータを保存します。
    - Click-Through Rate（クリック率）
    - Impression（表示回数）
    - Sales Conversion Rate（コンバージョン率）
    """
    __tablename__ = "analytics_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    recorded_date = Column(Date, nullable=False, index=True)

    # Analytics API メトリクス
    click_through_rate = Column(Numeric(5, 2), nullable=True)      # クリック率 (%)
    listing_impression = Column(Integer, default=0, nullable=False)  # 表示回数
    listing_views = Column(Integer, default=0, nullable=False)       # 閲覧数
    sales_conversion_rate = Column(Numeric(5, 2), nullable=True)   # コンバージョン率 (%)

    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # リレーションシップ
    listing = relationship("Listing", back_populates="analytics_metrics")

    # 複合インデックス（listing_id + recorded_date でユニーク）
    __table_args__ = (
        Index('ix_analytics_metrics_listing_date', 'listing_id', 'recorded_date', unique=True),
    )

    def __repr__(self):
        return (
            f"<AnalyticsMetric(id={self.id}, listing_id={self.listing_id}, "
            f"date={self.recorded_date}, ctr={self.click_through_rate}, "
            f"impressions={self.listing_impression})>"
        )
