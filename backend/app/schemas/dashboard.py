"""
Dashboard Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DashboardSummaryResponse(BaseModel):
    """ダッシュボードサマリーレスポンス"""
    active_listings: int = Field(..., description="アクティブな出品物数")
    total_views_today: int = Field(..., description="本日の総View数")
    total_watches_today: int = Field(..., description="本日の総Watch数")
    trending_items_count: int = Field(..., description="トレンド商品数")
    top_trending_score: float = Field(..., description="最高トレンドスコア")
    total_accounts: int = Field(..., description="接続済みアカウント数")


class DashboardPerformanceResponse(BaseModel):
    """ダッシュボードパフォーマンスレスポンス"""
    dates: List[str] = Field(..., description="日付リスト（ISO形式）")
    total_views: List[int] = Field(..., description="日別総View数")
    total_watches: List[int] = Field(..., description="日別総Watch数")
    avg_trend_score: List[float] = Field(..., description="日別平均トレンドスコア")
    trending_count: List[int] = Field(..., description="日別トレンド商品数")


class RecentActivity(BaseModel):
    """最近のアクティビティ"""
    listing_id: str
    item_id: str
    title: str
    price: Optional[float] = None
    currency: str
    updated_at: Optional[str] = None


class DashboardRecentActivitiesResponse(BaseModel):
    """最近のアクティビティレスポンス"""
    activities: List[RecentActivity]
