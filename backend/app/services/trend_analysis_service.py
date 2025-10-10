"""
Trend Analysis Service

トレンドスコアを計算し、TOP10商品を抽出するサービス
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.listing import Listing
from app.models.daily_metric import DailyMetric
from app.models.trend_analysis import TrendAnalysis
from app.models.ebay_account import EbayAccount

logger = logging.getLogger(__name__)


class TrendAnalysisService:
    """トレンド分析サービス"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_trend_score(
        self,
        listing_id: str,
        analysis_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        指定日のトレンドスコアを計算

        スコア計算式:
        Score = (View成長率 × 0.4) + (Watch成長率 × 0.4) + (価格勢い × 0.2)

        Args:
            listing_id: 出品物ID
            analysis_date: 分析対象日

        Returns:
            dict: {
                'trend_score': Decimal,
                'view_growth_rate': Decimal,
                'watch_growth_rate': Decimal,
                'view_7day_avg': Decimal,
                'watch_7day_avg': Decimal,
            } or None if insufficient data
        """
        # 当日のメトリクスを取得
        today_metric = self.db.query(DailyMetric).filter(
            DailyMetric.listing_id == listing_id,
            DailyMetric.recorded_date == analysis_date
        ).first()

        if not today_metric:
            logger.warning(f"No metric found for listing {listing_id} on {analysis_date}")
            return None

        # 前日のメトリクスを取得
        yesterday = analysis_date - timedelta(days=1)
        yesterday_metric = self.db.query(DailyMetric).filter(
            DailyMetric.listing_id == listing_id,
            DailyMetric.recorded_date == yesterday
        ).first()

        # 成長率計算
        view_growth_rate = Decimal('0.0')
        watch_growth_rate = Decimal('0.0')

        if yesterday_metric:
            # View成長率（前日比）
            if yesterday_metric.view_count > 0:
                view_growth_rate = Decimal(
                    ((today_metric.view_count - yesterday_metric.view_count) / yesterday_metric.view_count) * 100
                )
            elif today_metric.view_count > 0:
                # 前日0、当日>0の場合は100%成長とみなす
                view_growth_rate = Decimal('100.0')

            # Watch成長率（前日比）
            if yesterday_metric.watch_count > 0:
                watch_growth_rate = Decimal(
                    ((today_metric.watch_count - yesterday_metric.watch_count) / yesterday_metric.watch_count) * 100
                )
            elif today_metric.watch_count > 0:
                watch_growth_rate = Decimal('100.0')

        # 7日間移動平均を計算
        seven_days_ago = analysis_date - timedelta(days=6)
        metrics_7days = self.db.query(DailyMetric).filter(
            DailyMetric.listing_id == listing_id,
            DailyMetric.recorded_date >= seven_days_ago,
            DailyMetric.recorded_date <= analysis_date
        ).all()

        view_7day_avg = Decimal('0.0')
        watch_7day_avg = Decimal('0.0')

        if metrics_7days:
            total_views = sum(m.view_count for m in metrics_7days)
            total_watches = sum(m.watch_count for m in metrics_7days)
            days_count = len(metrics_7days)

            view_7day_avg = Decimal(total_views) / Decimal(days_count)
            watch_7day_avg = Decimal(total_watches) / Decimal(days_count)

        # 価格勢い（価格変動率）
        price_momentum = self._calculate_price_momentum(listing_id, analysis_date)

        # トレンドスコア計算
        # Score = (View成長率 × 0.4) + (Watch成長率 × 0.4) + (価格勢い × 0.2)
        trend_score = (
            view_growth_rate * Decimal('0.4') +
            watch_growth_rate * Decimal('0.4') +
            price_momentum * Decimal('0.2')
        )

        # スコアを0-100の範囲に正規化（負の成長率もあり得るので、最低0に）
        trend_score = max(Decimal('0.0'), trend_score)

        return {
            'trend_score': round(trend_score, 2),
            'view_growth_rate': round(view_growth_rate, 2),
            'watch_growth_rate': round(watch_growth_rate, 2),
            'view_7day_avg': round(view_7day_avg, 2),
            'watch_7day_avg': round(watch_7day_avg, 2),
        }

    def _calculate_price_momentum(
        self,
        listing_id: str,
        analysis_date: date
    ) -> Decimal:
        """
        価格勢いを計算（7日間の価格変動率）

        Args:
            listing_id: 出品物ID
            analysis_date: 分析対象日

        Returns:
            Decimal: 価格勢い（-100 ~ 100）
        """
        seven_days_ago = analysis_date - timedelta(days=6)

        # 過去7日間のメトリクスを取得
        metrics = self.db.query(DailyMetric).filter(
            DailyMetric.listing_id == listing_id,
            DailyMetric.recorded_date >= seven_days_ago,
            DailyMetric.recorded_date <= analysis_date,
            DailyMetric.current_price.isnot(None)
        ).order_by(DailyMetric.recorded_date.asc()).all()

        if len(metrics) < 2:
            return Decimal('0.0')

        # 最初と最後の価格を比較
        first_price = metrics[0].current_price
        last_price = metrics[-1].current_price

        if first_price is None or last_price is None or first_price == 0:
            return Decimal('0.0')

        # 価格変動率
        price_change_rate = ((last_price - first_price) / first_price) * 100

        # -100 ~ 100 の範囲に制限
        price_momentum = max(Decimal('-100.0'), min(Decimal('100.0'), Decimal(str(price_change_rate))))

        return price_momentum

    def analyze_listing(
        self,
        listing_id: str,
        analysis_date: date
    ) -> Optional[TrendAnalysis]:
        """
        単一出品物のトレンド分析を実行

        Args:
            listing_id: 出品物ID
            analysis_date: 分析対象日

        Returns:
            TrendAnalysis: 分析結果（保存済み）or None
        """
        result = self.calculate_trend_score(listing_id, analysis_date)

        if not result:
            return None

        # 既存の分析結果を確認
        existing = self.db.query(TrendAnalysis).filter(
            TrendAnalysis.listing_id == listing_id,
            TrendAnalysis.analysis_date == analysis_date
        ).first()

        if existing:
            # 更新
            existing.trend_score = result['trend_score']
            existing.view_growth_rate = result['view_growth_rate']
            existing.watch_growth_rate = result['watch_growth_rate']
            existing.view_7day_avg = result['view_7day_avg']
            existing.watch_7day_avg = result['watch_7day_avg']

            logger.info(f"Updated trend analysis for listing {listing_id} on {analysis_date}")
            trend_analysis = existing
        else:
            # 新規作成
            trend_analysis = TrendAnalysis(
                listing_id=listing_id,
                analysis_date=analysis_date,
                trend_score=result['trend_score'],
                view_growth_rate=result['view_growth_rate'],
                watch_growth_rate=result['watch_growth_rate'],
                view_7day_avg=result['view_7day_avg'],
                watch_7day_avg=result['watch_7day_avg'],
                is_trending=False,  # ランキング計算後に更新
            )
            self.db.add(trend_analysis)

            logger.info(f"Created trend analysis for listing {listing_id} on {analysis_date}")

        self.db.commit()
        self.db.refresh(trend_analysis)

        return trend_analysis

    def analyze_account(
        self,
        account_id: str,
        analysis_date: date
    ) -> List[TrendAnalysis]:
        """
        アカウント全体のトレンド分析を実行

        Args:
            account_id: eBayアカウントID
            analysis_date: 分析対象日

        Returns:
            List[TrendAnalysis]: 全出品物の分析結果
        """
        # アクティブな出品物を取得
        listings = self.db.query(Listing).filter(
            Listing.account_id == account_id,
            Listing.is_active == True
        ).all()

        logger.info(f"Analyzing {len(listings)} listings for account {account_id}")

        results = []
        for listing in listings:
            try:
                trend_analysis = self.analyze_listing(str(listing.id), analysis_date)
                if trend_analysis:
                    results.append(trend_analysis)
            except Exception as e:
                logger.error(f"Error analyzing listing {listing.id}: {e}")
                continue

        # ランキングを更新
        self._update_rankings(account_id, analysis_date)

        return results

    def _update_rankings(
        self,
        account_id: str,
        analysis_date: date,
        top_n: int = 10
    ):
        """
        トレンドスコアに基づいてランキングを更新し、TOP N商品をマーク

        Args:
            account_id: eBayアカウントID
            analysis_date: 分析対象日
            top_n: TOP N件（デフォルト10）
        """
        # アカウントの全出品物の分析結果を取得（スコア降順）
        trends = self.db.query(TrendAnalysis).join(
            Listing, TrendAnalysis.listing_id == Listing.id
        ).filter(
            Listing.account_id == account_id,
            TrendAnalysis.analysis_date == analysis_date
        ).order_by(TrendAnalysis.trend_score.desc()).all()

        # ランキングとis_trendingを更新
        for rank, trend in enumerate(trends, start=1):
            trend.rank = rank
            trend.is_trending = (rank <= top_n)

        self.db.commit()

        logger.info(f"Updated rankings for {len(trends)} items, TOP {top_n} marked as trending")

    def get_top_trending(
        self,
        account_id: str,
        analysis_date: date,
        limit: int = 10
    ) -> List[TrendAnalysis]:
        """
        指定日のトレンドTOP N商品を取得

        Args:
            account_id: eBayアカウントID
            analysis_date: 分析対象日
            limit: 取得件数（デフォルト10）

        Returns:
            List[TrendAnalysis]: TOP N商品
        """
        trends = self.db.query(TrendAnalysis).join(
            Listing, TrendAnalysis.listing_id == Listing.id
        ).filter(
            Listing.account_id == account_id,
            TrendAnalysis.analysis_date == analysis_date,
            TrendAnalysis.is_trending == True
        ).order_by(TrendAnalysis.rank.asc()).limit(limit).all()

        return trends

    def analyze_all_accounts(
        self,
        analysis_date: date
    ) -> Dict[str, Any]:
        """
        全アカウントのトレンド分析を実行

        Args:
            analysis_date: 分析対象日

        Returns:
            dict: {
                'total_accounts': int,
                'total_listings_analyzed': int,
                'accounts_processed': List[str],
            }
        """
        # 全アクティブアカウントを取得
        accounts = self.db.query(EbayAccount).filter(
            EbayAccount.is_active == True
        ).all()

        logger.info(f"Starting trend analysis for {len(accounts)} accounts on {analysis_date}")

        total_listings = 0
        accounts_processed = []

        for account in accounts:
            try:
                results = self.analyze_account(str(account.id), analysis_date)
                total_listings += len(results)
                accounts_processed.append(str(account.id))

                logger.info(f"Account {account.id}: analyzed {len(results)} listings")
            except Exception as e:
                logger.error(f"Error analyzing account {account.id}: {e}")
                continue

        logger.info(
            f"Trend analysis completed: {len(accounts_processed)} accounts, "
            f"{total_listings} listings analyzed"
        )

        return {
            'total_accounts': len(accounts_processed),
            'total_listings_analyzed': total_listings,
            'accounts_processed': accounts_processed,
        }
