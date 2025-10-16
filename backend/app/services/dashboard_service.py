"""
Dashboard Service

ダッシュボード用のKPIとパフォーマンスデータを集計するサービス
"""
import logging
from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.listing import Listing
from app.models.daily_metric import DailyMetric
from app.models.trend_analysis import TrendAnalysis
from app.models.ebay_account import EbayAccount
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class DashboardService:
    """ダッシュボードサービス"""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, tenant: Tenant, account_id: str = None) -> Dict[str, Any]:
        """
        KPIサマリーを取得

        Args:
            tenant: テナント
            account_id: 特定アカウントのみ取得（Noneの場合は全アカウント）

        Returns:
            dict: {
                'active_listings': int,
                'total_views_today': int,
                'total_watches_today': int,
                'trending_items_count': int,
                'top_trending_score': float,
                'total_accounts': int
            }
        """
        today = date.today()

        # テナントのアカウント一覧を取得（account_idが指定されている場合はフィルタリング）
        query = self.db.query(EbayAccount.id).filter(
            EbayAccount.tenant_id == tenant.id,
            EbayAccount.is_active == True
        )

        if account_id:
            query = query.filter(EbayAccount.id == account_id)

        account_ids = query.all()
        account_ids = [acc[0] for acc in account_ids]

        if not account_ids:
            return {
                'active_listings': 0,
                'total_views_today': 0,
                'total_watches_today': 0,
                'trending_items_count': 0,
                'top_trending_score': 0.0,
                'total_accounts': 0
            }

        # アクティブな出品物数
        active_listings = self.db.query(func.count(Listing.id)).filter(
            Listing.account_id.in_(account_ids),
            Listing.is_active == True
        ).scalar() or 0

        # 本日のメトリクス合計
        today_metrics = self.db.query(
            func.sum(DailyMetric.view_count).label('total_views'),
            func.sum(DailyMetric.watch_count).label('total_watches')
        ).join(
            Listing, DailyMetric.listing_id == Listing.id
        ).filter(
            Listing.account_id.in_(account_ids),
            DailyMetric.recorded_date == today
        ).first()

        total_views_today = int(today_metrics.total_views or 0)
        total_watches_today = int(today_metrics.total_watches or 0)

        # トレンド商品数（本日）
        trending_items_count = self.db.query(func.count(TrendAnalysis.id)).join(
            Listing, TrendAnalysis.listing_id == Listing.id
        ).filter(
            Listing.account_id.in_(account_ids),
            TrendAnalysis.analysis_date == today,
            TrendAnalysis.is_trending == True
        ).scalar() or 0

        # 最高トレンドスコア
        top_trending = self.db.query(
            func.max(TrendAnalysis.trend_score)
        ).join(
            Listing, TrendAnalysis.listing_id == Listing.id
        ).filter(
            Listing.account_id.in_(account_ids),
            TrendAnalysis.analysis_date == today
        ).scalar()

        top_trending_score = float(top_trending or 0.0)

        return {
            'active_listings': active_listings,
            'total_views_today': total_views_today,
            'total_watches_today': total_watches_today,
            'trending_items_count': trending_items_count,
            'top_trending_score': round(top_trending_score, 2),
            'total_accounts': len(account_ids)
        }

    def get_performance(
        self,
        tenant: Tenant,
        days: int = 7,
        account_id: str = None
    ) -> Dict[str, Any]:
        """
        パフォーマンス推移を取得（過去N日間）

        Args:
            tenant: テナント
            days: 取得日数（デフォルト7日間）
            account_id: 特定アカウントのみ取得（Noneの場合は全アカウント）

        Returns:
            dict: {
                'dates': List[str],
                'total_views': List[int],
                'total_watches': List[int],
                'avg_trend_score': List[float],
                'trending_count': List[int]
            }
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # テナントのアカウント一覧を取得（account_idが指定されている場合はフィルタリング）
        query = self.db.query(EbayAccount.id).filter(
            EbayAccount.tenant_id == tenant.id,
            EbayAccount.is_active == True
        )

        if account_id:
            query = query.filter(EbayAccount.id == account_id)

        account_ids = query.all()
        account_ids = [acc[0] for acc in account_ids]

        if not account_ids:
            return {
                'dates': [],
                'total_views': [],
                'total_watches': [],
                'avg_trend_score': [],
                'trending_count': []
            }

        # 日付リストを生成
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)

        # 各日付のメトリクス合計を取得
        daily_metrics = self.db.query(
            DailyMetric.recorded_date,
            func.sum(DailyMetric.view_count).label('total_views'),
            func.sum(DailyMetric.watch_count).label('total_watches')
        ).join(
            Listing, DailyMetric.listing_id == Listing.id
        ).filter(
            Listing.account_id.in_(account_ids),
            DailyMetric.recorded_date >= start_date,
            DailyMetric.recorded_date <= end_date
        ).group_by(
            DailyMetric.recorded_date
        ).order_by(
            DailyMetric.recorded_date
        ).all()

        # メトリクスを辞書に変換
        metrics_dict = {
            metric.recorded_date: {
                'views': int(metric.total_views or 0),
                'watches': int(metric.total_watches or 0)
            }
            for metric in daily_metrics
        }

        # トレンド分析データを取得
        trend_data = self.db.query(
            TrendAnalysis.analysis_date,
            func.avg(TrendAnalysis.trend_score).label('avg_score'),
            func.count(
                func.nullif(TrendAnalysis.is_trending, False)
            ).label('trending_count')
        ).join(
            Listing, TrendAnalysis.listing_id == Listing.id
        ).filter(
            Listing.account_id.in_(account_ids),
            TrendAnalysis.analysis_date >= start_date,
            TrendAnalysis.analysis_date <= end_date
        ).group_by(
            TrendAnalysis.analysis_date
        ).order_by(
            TrendAnalysis.analysis_date
        ).all()

        # トレンドデータを辞書に変換
        trend_dict = {
            trend.analysis_date: {
                'avg_score': float(trend.avg_score or 0.0),
                'trending_count': int(trend.trending_count or 0)
            }
            for trend in trend_data
        }

        # 結果を構築
        dates = []
        total_views = []
        total_watches = []
        avg_trend_score = []
        trending_count = []

        for d in date_list:
            dates.append(d.isoformat())

            # メトリクスデータ
            metrics = metrics_dict.get(d, {'views': 0, 'watches': 0})
            total_views.append(metrics['views'])
            total_watches.append(metrics['watches'])

            # トレンドデータ
            trend = trend_dict.get(d, {'avg_score': 0.0, 'trending_count': 0})
            avg_trend_score.append(round(trend['avg_score'], 2))
            trending_count.append(trend['trending_count'])

        return {
            'dates': dates,
            'total_views': total_views,
            'total_watches': total_watches,
            'avg_trend_score': avg_trend_score,
            'trending_count': trending_count
        }

    def get_recent_activities(
        self,
        tenant: Tenant,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        最近のアクティビティを取得

        Args:
            tenant: テナント
            limit: 取得件数

        Returns:
            List[dict]: 最近の変更があった出品物
        """
        # テナントのアカウント一覧を取得
        account_ids = self.db.query(EbayAccount.id).filter(
            EbayAccount.tenant_id == tenant.id,
            EbayAccount.is_active == True
        ).all()
        account_ids = [acc[0] for acc in account_ids]

        if not account_ids:
            return []

        # 最近更新された出品物を取得
        recent_listings = self.db.query(Listing).filter(
            Listing.account_id.in_(account_ids),
            Listing.is_active == True
        ).order_by(
            Listing.updated_at.desc()
        ).limit(limit).all()

        activities = []
        for listing in recent_listings:
            activities.append({
                'listing_id': str(listing.id),
                'item_id': listing.item_id,
                'title': listing.title,
                'price': float(listing.price) if listing.price else None,
                'currency': listing.currency,
                'updated_at': listing.updated_at.isoformat() if listing.updated_at else None
            })

        return activities
