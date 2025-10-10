"""
Analytics Sync Service

Analytics APIからトラフィックデータを取得して保存
"""
import logging
from datetime import date
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.listing import Listing
from app.models.analytics_metric import AnalyticsMetric
from app.models.ebay_account import EbayAccount
from app.clients.analytics_api_client import AnalyticsAPIClient
from app.services.ebay_oauth_service import EbayOAuthService

logger = logging.getLogger(__name__)


class AnalyticsSyncService:
    """Analytics同期サービス"""

    def __init__(self, db: Session):
        self.db = db
        self.analytics_client = AnalyticsAPIClient()
        self.oauth_service = EbayOAuthService()

    async def sync_account_analytics(
        self,
        account: EbayAccount,
        recorded_date: date = None
    ) -> Dict[str, Any]:
        """
        アカウントのAnalyticsデータを同期

        Args:
            account: eBayアカウント
            recorded_date: 記録日（Noneの場合は今日）

        Returns:
            dict: 同期結果
        """
        if not recorded_date:
            recorded_date = date.today()

        logger.info(f"Starting analytics sync for account {account.id} on {recorded_date}")

        # アクセストークンを取得
        access_token = await self.oauth_service.get_valid_access_token(self.db, account.tenant_id)

        if not access_token:
            raise Exception(f"No valid access token for account {account.id}")

        # アカウントのアクティブ出品物を取得
        listings = self.db.query(Listing).filter(
            Listing.account_id == account.id,
            Listing.is_active == True
        ).all()

        if not listings:
            logger.warning(f"No active listings found for account {account.id}")
            return {
                'total_listings': 0,
                'synced': 0
            }

        # 出品物IDリストを作成
        listing_ids = [listing.item_id for listing in listings]

        # Analyticsデータを取得（50件ずつ）
        synced_count = 0
        batch_size = 50

        for i in range(0, len(listing_ids), batch_size):
            batch_ids = listing_ids[i:i + batch_size]

            try:
                # Analytics APIからデータ取得
                traffic_data = self.analytics_client.get_listing_traffic(
                    access_token=access_token,
                    listing_ids=batch_ids
                )

                # データをパースして保存
                synced_count += self._save_analytics_data(
                    traffic_data,
                    listings,
                    recorded_date
                )

            except Exception as e:
                logger.error(f"Failed to sync analytics batch {i}-{i+batch_size}: {e}")
                continue

        logger.info(f"Analytics sync completed: {synced_count}/{len(listings)} listings")

        return {
            'total_listings': len(listings),
            'synced': synced_count
        }

    def _save_analytics_data(
        self,
        traffic_data: Dict[str, Any],
        listings: List[Listing],
        recorded_date: date
    ) -> int:
        """
        Analyticsデータをデータベースに保存

        Args:
            traffic_data: Analytics APIレスポンス
            listings: 出品物リスト
            recorded_date: 記録日

        Returns:
            int: 保存件数
        """
        # item_id -> listing のマッピング
        listing_map = {listing.item_id: listing for listing in listings}

        synced_count = 0

        for record in traffic_data.get('records', []):
            try:
                # item_idを取得
                item_id = None
                for dim_value in record.get('dimensionValues', []):
                    if dim_value.get('dimension') == 'LISTING':
                        item_id = dim_value.get('value')
                        break

                if not item_id or item_id not in listing_map:
                    continue

                listing = listing_map[item_id]

                # メトリクス値を取得
                metrics = {}
                for metric_value in record.get('metricValues', []):
                    metric_name = metric_value.get('metric')
                    value = metric_value.get('value')

                    if metric_name == 'CLICK_THROUGH_RATE':
                        metrics['click_through_rate'] = Decimal(value) if value else None
                    elif metric_name == 'LISTING_IMPRESSION':
                        metrics['listing_impression'] = int(value) if value else 0
                    elif metric_name == 'LISTING_VIEWS':
                        metrics['listing_views'] = int(value) if value else 0
                    elif metric_name == 'SALES_CONVERSION_RATE':
                        metrics['sales_conversion_rate'] = Decimal(value) if value else None

                # 既存レコードを確認
                existing = self.db.query(AnalyticsMetric).filter(
                    AnalyticsMetric.listing_id == listing.id,
                    AnalyticsMetric.recorded_date == recorded_date
                ).first()

                if existing:
                    # 更新
                    for key, value in metrics.items():
                        setattr(existing, key, value)
                else:
                    # 新規作成
                    analytics_metric = AnalyticsMetric(
                        listing_id=listing.id,
                        recorded_date=recorded_date,
                        **metrics
                    )
                    self.db.add(analytics_metric)

                synced_count += 1

            except Exception as e:
                logger.error(f"Failed to save analytics data for item {item_id}: {e}")
                continue

        self.db.commit()
        return synced_count

    async def sync_all_accounts_analytics(
        self,
        recorded_date: date = None
    ) -> Dict[str, Any]:
        """
        全アカウントのAnalyticsデータを同期

        Args:
            recorded_date: 記録日

        Returns:
            dict: 同期結果
        """
        accounts = self.db.query(EbayAccount).filter(
            EbayAccount.is_active == True
        ).all()

        logger.info(f"Starting analytics sync for {len(accounts)} accounts")

        total_synced = 0
        accounts_processed = []

        for account in accounts:
            try:
                result = await self.sync_account_analytics(account, recorded_date)
                total_synced += result['synced']
                accounts_processed.append(str(account.id))

            except Exception as e:
                logger.error(f"Failed to sync analytics for account {account.id}: {e}")
                continue

        logger.info(f"Analytics sync completed: {total_synced} listings, {len(accounts_processed)} accounts")

        return {
            'total_accounts': len(accounts_processed),
            'total_synced': total_synced,
            'accounts_processed': accounts_processed
        }
