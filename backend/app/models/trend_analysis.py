"""
TrendAnalysis Model
"""
from sqlalchemy import Column, String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey, UUID, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class TrendAnalysis(Base):
    """
    トレンド分析結果を保存するモデル

    毎日の分析結果として、各出品物のトレンドスコアを計算し保存します。
    - View成長率、Watch成長率を計算
    - 7日間移動平均を算出
    - トレンドスコアでランキング
    - 上位商品をis_trending=Trueでマーク
    """
    __tablename__ = "trend_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    analysis_date = Column(Date, nullable=False, index=True)

    # 成長率（前日比、パーセント）
    view_growth_rate = Column(Numeric(8, 2), nullable=True)  # -999.99 ~ 999.99
    watch_growth_rate = Column(Numeric(8, 2), nullable=True)

    # 7日間移動平均
    view_7day_avg = Column(Numeric(10, 2), nullable=True)
    watch_7day_avg = Column(Numeric(10, 2), nullable=True)

    # トレンドスコア（0.00 ~ 100.00）
    trend_score = Column(Numeric(10, 2), nullable=False, index=True)

    # ランキング（1位、2位、...）
    rank = Column(Integer, nullable=True, index=True)

    # トレンド商品フラグ（TOP10など）
    is_trending = Column(Boolean, default=False, nullable=False, index=True)

    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # リレーションシップ
    listing = relationship("Listing", back_populates="trend_analyses")

    # 複合インデックス
    __table_args__ = (
        Index('ix_trend_analysis_listing_date', 'listing_id', 'analysis_date', unique=True),
        Index('ix_trend_analysis_date_score', 'analysis_date', 'trend_score'),
        Index('ix_trend_analysis_date_trending', 'analysis_date', 'is_trending'),
    )

    def __repr__(self):
        return (
            f"<TrendAnalysis(id={self.id}, listing_id={self.listing_id}, "
            f"date={self.analysis_date}, score={self.trend_score}, rank={self.rank})>"
        )
