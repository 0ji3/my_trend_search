"""
Feed Sync Service

Feed APIを使って大量のデータを一括取得（初回同期の高速化）
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.listing import Listing
from app.models.ebay_account import EbayAccount
from app.clients.feed_api_client import FeedAPIClient
from app.services.ebay_oauth_service import EbayOAuthService

logger = logging.getLogger(__name__)


class FeedSyncService:
    """Feed同期サービス"""

    def __init__(self, db: Session):
        self.db = db
        self.feed_client = FeedAPIClient()
        self.oauth_service = EbayOAuthService()

    async def bulk_sync_account(
        self,
        account: EbayAccount,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Feed APIを使って一括同期（初回同期向け）

        Args:
            account: eBayアカウント
            wait_for_completion: 完了まで待機するか（Falseの場合はタスクIDのみ返す）

        Returns:
            dict: 同期結果
        """
        logger.info(f"Starting bulk sync for account {account.id} using Feed API")

        # アクセストークンを取得
        access_token = await self.oauth_service.get_valid_access_token(self.db, account.tenant_id)

        if not access_token:
            raise Exception(f"No valid access token for account {account.id}")

        try:
            # Feed APIで在庫データを取得
            listings_data = self.feed_client.get_inventory_feed(
                access_token=access_token,
                marketplace_id=account.marketplace_id or "EBAY_US",
                wait_for_completion=wait_for_completion,
                max_wait_seconds=300  # 5分
            )

            if not wait_for_completion:
                logger.info("Feed task created, will complete in background")
                return {
                    'status': 'queued',
                    'message': 'Feed task created, check back later'
                }

            # データを保存
            synced_count = self._save_feed_listings(listings_data, account)

            logger.info(f"Bulk sync completed: {synced_count} listings synced")

            return {
                'status': 'completed',
                'total_listings': len(listings_data),
                'synced': synced_count
            }

        except Exception as e:
            logger.error(f"Bulk sync failed for account {account.id}: {e}")
            raise

    def _save_feed_listings(
        self,
        listings_data: List[Dict[str, Any]],
        account: EbayAccount
    ) -> int:
        """
        Feed APIから取得したデータを保存

        Args:
            listings_data: Feed APIレスポンスデータ
            account: eBayアカウント

        Returns:
            int: 保存件数
        """
        synced_count = 0

        for item_data in listings_data:
            try:
                item_id = item_data.get('itemId')
                if not item_id:
                    continue

                # 価格情報を取得
                price_info = item_data.get('price', {})
                price = Decimal(price_info.get('value', '0')) if price_info else None
                currency = price_info.get('currency', 'USD')

                # 画像URL（最初の1枚）
                image_urls = item_data.get('imageUrls', [])
                image_url = image_urls[0] if image_urls else None

                # 既存のListingを確認
                existing = self.db.query(Listing).filter(
                    Listing.account_id == account.id,
                    Listing.item_id == item_id
                ).first()

                if existing:
                    # 更新
                    existing.title = item_data.get('title', existing.title)
                    existing.price = price
                    existing.currency = currency
                    existing.category_id = item_data.get('categoryId')
                    existing.category_name = item_data.get('categoryName')
                    existing.is_active = item_data.get('listingStatus') == 'ACTIVE'
                    existing.image_url = image_url
                    existing.listing_type = item_data.get('listingType')
                    existing.listing_status = item_data.get('listingStatus')
                    existing.quantity = item_data.get('quantity')
                    existing.quantity_sold = item_data.get('quantitySold')
                    existing.item_specifics = item_data.get('itemSpecifics')

                else:
                    # 新規作成
                    listing = Listing(
                        account_id=account.id,
                        item_id=item_id,
                        title=item_data.get('title', ''),
                        price=price,
                        currency=currency,
                        category_id=item_data.get('categoryId'),
                        category_name=item_data.get('categoryName'),
                        is_active=item_data.get('listingStatus') == 'ACTIVE',
                        image_url=image_url,
                        listing_type=item_data.get('listingType'),
                        listing_status=item_data.get('listingStatus'),
                        quantity=item_data.get('quantity'),
                        quantity_sold=item_data.get('quantitySold'),
                        item_specifics=item_data.get('itemSpecifics')
                    )
                    self.db.add(listing)

                synced_count += 1

            except Exception as e:
                logger.error(f"Failed to save listing {item_id}: {e}")
                continue

        self.db.commit()
        return synced_count

    async def bulk_sync_all_accounts(self) -> Dict[str, Any]:
        """
        全アカウントをFeed APIで一括同期

        Returns:
            dict: 同期結果
        """
        accounts = self.db.query(EbayAccount).filter(
            EbayAccount.is_active == True
        ).all()

        logger.info(f"Starting bulk sync for {len(accounts)} accounts")

        total_synced = 0
        accounts_processed = []

        for account in accounts:
            try:
                result = await self.bulk_sync_account(account, wait_for_completion=True)
                if result['status'] == 'completed':
                    total_synced += result['synced']
                    accounts_processed.append(str(account.id))

            except Exception as e:
                logger.error(f"Failed to bulk sync account {account.id}: {e}")
                continue

        logger.info(f"Bulk sync completed: {total_synced} listings, {len(accounts_processed)} accounts")

        return {
            'total_accounts': len(accounts_processed),
            'total_synced': total_synced,
            'accounts_processed': accounts_processed
        }
