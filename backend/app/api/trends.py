"""
Trend Analysis API Endpoints

トレンド分析結果を取得するAPIエンドポイント
"""
import logging
from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.tenant import Tenant
from app.models.listing import Listing
from app.models.trend_analysis import TrendAnalysis
from app.api.auth import get_current_tenant
from app.schemas.trend import (
    TrendAnalysisResponse,
    TopTrendingRequest,
    TopTrendingResponse,
    TrendAnalysisWithListing,
    TrendHistoryRequest,
    TrendHistoryResponse,
    AnalyzeTriggerRequest,
    AnalyzeTriggerResponse,
)
from app.services.trend_analysis_service import TrendAnalysisService
from app.tasks.trend_analysis import analyze_all_trends, analyze_single_account

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/top", response_model=TopTrendingResponse)
def get_top_trending(
    analysis_date: date = Query(default=None, description="分析対象日（未指定の場合は最新）"),
    limit: int = Query(default=10, ge=1, le=100, description="取得件数"),
    account_id: UUID = Query(default=None, description="特定アカウントのみ取得"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    トレンドTOP N商品を取得

    指定日（または最新）のトレンドスコアが高い商品を取得します。
    """
    # 分析対象日を決定
    if not analysis_date:
        # 最新の分析日を取得
        latest_analysis = db.query(TrendAnalysis).order_by(
            TrendAnalysis.analysis_date.desc()
        ).first()

        if not latest_analysis:
            # 分析結果がない場合は今日を使用
            analysis_date = date.today()
        else:
            analysis_date = latest_analysis.analysis_date

    # クエリを構築
    # テナントのeBayアカウントIDを取得
    from app.models.ebay_account import EbayAccount
    tenant_account_ids = db.query(EbayAccount.id).filter(
        EbayAccount.tenant_id == current_tenant.id,
        EbayAccount.is_active == True
    ).subquery()

    query = db.query(
        TrendAnalysis,
        Listing.item_id,
        Listing.title,
        Listing.price,
        Listing.currency,
        Listing.image_url,
        Listing.category_name
    ).join(
        Listing, TrendAnalysis.listing_id == Listing.id
    ).filter(
        Listing.account_id.in_(tenant_account_ids),
        TrendAnalysis.analysis_date == analysis_date,
        TrendAnalysis.is_trending == True
    )

    # 特定アカウントの指定がある場合
    if account_id:
        query = query.filter(Listing.account_id == account_id)

    # ランキング順で取得
    results = query.order_by(TrendAnalysis.rank.asc()).limit(limit).all()

    # レスポンスを構築
    trends = []
    for trend, item_id, title, price, currency, image_url, category_name in results:
        trends.append(TrendAnalysisWithListing(
            id=trend.id,
            listing_id=trend.listing_id,
            analysis_date=trend.analysis_date,
            view_growth_rate=trend.view_growth_rate,
            watch_growth_rate=trend.watch_growth_rate,
            view_7day_avg=trend.view_7day_avg,
            watch_7day_avg=trend.watch_7day_avg,
            trend_score=trend.trend_score,
            rank=trend.rank,
            is_trending=trend.is_trending,
            created_at=trend.created_at,
            item_id=item_id,
            title=title,
            price=price,
            currency=currency,
            image_url=image_url,
            category_name=category_name
        ))

    return TopTrendingResponse(
        analysis_date=analysis_date,
        total_count=len(trends),
        trends=trends
    )


@router.get("/listing/{listing_id}/history", response_model=TrendHistoryResponse)
def get_listing_trend_history(
    listing_id: UUID,
    start_date: date = Query(default=None, description="開始日"),
    end_date: date = Query(default=None, description="終了日"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    特定商品のトレンド履歴を取得

    指定期間（デフォルト7日間）のトレンド推移を取得します。
    """
    # 出品物を取得（権限チェック）
    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )

    # テナントの所有確認（listing.account.tenant_id == current_tenant.id）
    # TODO: この確認はより厳密に行うべき

    # 期間を決定
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=6)  # 7日間

    # トレンド履歴を取得
    history = db.query(TrendAnalysis).filter(
        TrendAnalysis.listing_id == listing_id,
        TrendAnalysis.analysis_date >= start_date,
        TrendAnalysis.analysis_date <= end_date
    ).order_by(TrendAnalysis.analysis_date.asc()).all()

    return TrendHistoryResponse(
        listing_id=listing.id,
        item_id=listing.item_id,
        title=listing.title,
        start_date=start_date,
        end_date=end_date,
        history=[TrendAnalysisResponse.model_validate(t) for t in history]
    )


@router.post("/analyze", response_model=AnalyzeTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_trend_analysis(
    request: AnalyzeTriggerRequest = AnalyzeTriggerRequest(),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    トレンド分析を手動トリガー

    指定アカウント（または全アカウント）のトレンド分析をバックグラウンドで実行します。
    """
    # 分析対象日を決定
    target_date = request.analysis_date if request.analysis_date else date.today()
    target_date_str = str(target_date)

    # タスクを実行
    if request.account_id:
        # 特定アカウントのみ
        # TODO: アカウントの所有権確認
        task = analyze_single_account.delay(str(request.account_id), target_date_str)
        message = f"Trend analysis queued for account {request.account_id}"
    else:
        # 全アカウント
        task = analyze_all_trends.delay(target_date_str)
        message = "Trend analysis queued for all accounts"

    logger.info(f"Trend analysis triggered: task_id={task.id}, date={target_date_str}")

    return AnalyzeTriggerResponse(
        status="accepted",
        task_id=task.id,
        message=message
    )


@router.get("/analysis-dates", response_model=List[date])
def get_available_analysis_dates(
    limit: int = Query(default=30, ge=1, le=365, description="取得件数"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    利用可能な分析日一覧を取得

    トレンド分析が実行された日付のリストを返します。
    """
    # ユニークな分析日を取得
    dates = db.query(TrendAnalysis.analysis_date).distinct().order_by(
        TrendAnalysis.analysis_date.desc()
    ).limit(limit).all()

    return [d[0] for d in dates]
