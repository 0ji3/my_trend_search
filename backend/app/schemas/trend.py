"""
Trend Analysis Pydantic Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


class TrendAnalysisBase(BaseModel):
    """トレンド分析ベーススキーマ"""
    analysis_date: date
    view_growth_rate: Optional[Decimal] = None
    watch_growth_rate: Optional[Decimal] = None
    view_7day_avg: Optional[Decimal] = None
    watch_7day_avg: Optional[Decimal] = None
    trend_score: Decimal
    rank: Optional[int] = None
    is_trending: bool = False


class TrendAnalysisCreate(TrendAnalysisBase):
    """トレンド分析作成スキーマ"""
    listing_id: UUID


class TrendAnalysisUpdate(BaseModel):
    """トレンド分析更新スキーマ"""
    trend_score: Optional[Decimal] = None
    rank: Optional[int] = None
    is_trending: Optional[bool] = None


class TrendAnalysisInDB(TrendAnalysisBase):
    """DB内トレンド分析スキーマ"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    listing_id: UUID
    created_at: datetime


class TrendAnalysisWithListing(TrendAnalysisInDB):
    """出品物情報付きトレンド分析スキーマ"""
    # Listing info
    item_id: str
    title: str
    price: Optional[Decimal] = None
    currency: str
    image_url: Optional[str] = None
    category_name: Optional[str] = None


class TrendAnalysisResponse(TrendAnalysisInDB):
    """トレンド分析APIレスポンス"""
    pass


class TopTrendingRequest(BaseModel):
    """TOP N取得リクエスト"""
    analysis_date: Optional[date] = Field(
        default=None,
        description="分析対象日（未指定の場合は最新）"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="取得件数（1-100）"
    )


class TopTrendingResponse(BaseModel):
    """TOP Nレスポンス"""
    analysis_date: date
    total_count: int
    trends: list[TrendAnalysisWithListing]


class TrendHistoryRequest(BaseModel):
    """トレンド履歴取得リクエスト"""
    start_date: Optional[date] = Field(
        default=None,
        description="開始日（未指定の場合は7日前）"
    )
    end_date: Optional[date] = Field(
        default=None,
        description="終了日（未指定の場合は今日）"
    )


class TrendHistoryResponse(BaseModel):
    """トレンド履歴レスポンス"""
    listing_id: UUID
    item_id: str
    title: str
    start_date: date
    end_date: date
    history: list[TrendAnalysisInDB]


class AnalyzeTriggerRequest(BaseModel):
    """トレンド分析トリガーリクエスト"""
    account_id: Optional[UUID] = Field(
        default=None,
        description="特定アカウントのみ分析（未指定の場合は全アカウント）"
    )
    analysis_date: Optional[date] = Field(
        default=None,
        description="分析対象日（未指定の場合は今日）"
    )


class AnalyzeTriggerResponse(BaseModel):
    """トレンド分析トリガーレスポンス"""
    status: str
    task_id: str
    message: str
