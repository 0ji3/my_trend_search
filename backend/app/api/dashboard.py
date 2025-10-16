"""
Dashboard API Endpoints

ダッシュボード用のKPIとパフォーマンスデータを提供するAPI
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tenant import Tenant
from app.api.auth import get_current_tenant
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardPerformanceResponse,
    DashboardRecentActivitiesResponse
)
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    account_id: str = Query(None, description="特定アカウントのみ取得（未指定の場合は全アカウント）"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    ダッシュボードのKPIサマリーを取得

    - アクティブな出品物数
    - 本日の総View数・Watch数
    - トレンド商品数
    - 最高トレンドスコア
    - 接続済みアカウント数
    """
    service = DashboardService(db)
    summary = service.get_summary(current_tenant, account_id=account_id)

    logger.info(f"Dashboard summary fetched for tenant {current_tenant.id}, account: {account_id or 'all'}")

    return DashboardSummaryResponse(**summary)


@router.get("/performance", response_model=DashboardPerformanceResponse)
def get_dashboard_performance(
    days: int = Query(default=7, ge=1, le=30, description="取得日数（1-30日）"),
    account_id: str = Query(None, description="特定アカウントのみ取得（未指定の場合は全アカウント）"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    パフォーマンス推移を取得

    過去N日間の以下のデータを取得：
    - 日別総View数・Watch数
    - 日別平均トレンドスコア
    - 日別トレンド商品数
    """
    service = DashboardService(db)
    performance = service.get_performance(current_tenant, days, account_id=account_id)

    logger.info(f"Dashboard performance fetched for tenant {current_tenant.id} ({days} days), account: {account_id or 'all'}")

    return DashboardPerformanceResponse(**performance)


@router.get("/recent-activities", response_model=DashboardRecentActivitiesResponse)
def get_recent_activities(
    limit: int = Query(default=10, ge=1, le=50, description="取得件数（1-50）"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    最近のアクティビティを取得

    最近更新された出品物のリストを返します。
    """
    service = DashboardService(db)
    activities = service.get_recent_activities(current_tenant, limit)

    logger.info(f"Recent activities fetched for tenant {current_tenant.id}")

    return DashboardRecentActivitiesResponse(activities=activities)
