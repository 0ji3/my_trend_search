"""
eBay Data Synchronization Service
Handles syncing listing data and metrics from eBay
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.models import EbayAccount, Listing, DailyMetric
from app.clients.trading_api_client import TradingAPIClient
from app.services.ebay_oauth_service import EbayOAuthService
from app.services.rate_limiter import RateLimiter
from app.services.cache_service import CacheService
from app.clients.ebay_client_base import EbayRateLimitError

logger = logging.getLogger(__name__)


class EbayDataSyncService:
    """
    Service for synchronizing eBay listing data

    Responsibilities:
    - Fetch active listings from eBay
    - Update listings table
    - Record daily metrics (views, watches, bids)
    - Handle errors and retries
    """

    def __init__(self, db: Session):
        self.db = db
        self.oauth_service = EbayOAuthService()
        self.trading_client = TradingAPIClient()
        self.rate_limiter = RateLimiter()
        self.cache_service = CacheService()

    async def sync_account_listings(self, account: EbayAccount) -> Dict[str, Any]:
        """
        Sync all active listings for one eBay account (Memory-Optimized with Batch Processing)

        Steps:
        1. Get valid access token
        2. Fetch items page by page (200 items at a time)
        3. For each item: GetItem to get View/Watch counts
        4. Update listings table (upsert)
        5. Insert daily_metrics record
        6. Clear memory every 100 items to prevent OOM

        Args:
            account: EbayAccount model instance

        Returns:
            {
                'account_id': str,
                'items_synced': int,
                'items_failed': int,
                'sync_time': datetime,
                'errors': List[str]
            }
        """
        logger.info(f"Starting sync for account {account.id} (eBay User: {account.ebay_user_id})")

        # Check if already synced today
        if self.cache_service.is_synced_today(str(account.id), "trading"):
            logger.info(f"Account {account.id} already synced today, skipping")
            return {
                'account_id': str(account.id),
                'items_synced': 0,
                'items_failed': 0,
                'sync_time': account.last_sync_at,
                'errors': [],
                'cached': True
            }

        errors = []
        synced_count = 0
        failed_count = 0
        COMMIT_BATCH_SIZE = 100  # Commit and clear memory every 100 items

        try:
            # Get valid OAuth token
            access_token = await self.oauth_service.get_valid_access_token(
                self.db,
                account.tenant_id
            )

            # === BATCH PROCESSING: Fetch and process page by page ===
            page = 1
            entries_per_page = 200
            total_items_found = 0

            while True:
                # Check rate limit before API call
                if not self.rate_limiter.check_rate_limit(str(account.tenant_id), "trading", 1):
                    raise EbayRateLimitError("Trading API rate limit reached for today")

                # Fetch one page at a time (200 items max)
                result = self.trading_client.get_my_ebay_selling(
                    access_token,
                    page_number=page,
                    entries_per_page=entries_per_page
                )

                # Record API call
                self.rate_limiter.record_api_call(str(account.tenant_id), "trading", 1)

                items_batch = result['items']
                total_pages = result['total_pages']
                total_items_found += len(items_batch)

                logger.info(
                    f"Processing page {page}/{total_pages} "
                    f"({len(items_batch)} items, total: {total_items_found})"
                )

                # Process items in this page
                for item_summary in items_batch:
                    try:
                        item_id = item_summary['item_id']
                        if not item_id:
                            continue

                        # Get detailed item data including View/Watch
                        item_data = self.trading_client.get_item(item_id, access_token)

                        # Upsert listing
                        listing = self._upsert_listing(account, item_data)

                        # Insert daily metric
                        self._insert_daily_metric(listing, item_data)

                        synced_count += 1

                        # === MEMORY OPTIMIZATION: Clear session every 100 items ===
                        if synced_count % COMMIT_BATCH_SIZE == 0:
                            self.db.commit()
                            self.db.expunge_all()  # Remove objects from session to free memory
                            logger.info(f"✓ Memory cleared after {synced_count} items")

                    except Exception as e:
                        failed_count += 1
                        error_msg = f"Failed to sync item {item_summary.get('item_id')}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        # Continue with other items

                # === Commit after each page ===
                self.db.commit()
                self.db.expunge_all()  # Clear memory after each page
                logger.info(f"✓ Page {page} completed, memory cleared")

                # Check if we've reached the last page
                if page >= total_pages:
                    break

                page += 1

            # Final commit for any remaining items
            self.db.commit()

            # Update last_sync_at (refresh account object first)
            self.db.refresh(account)
            account.last_sync_at = datetime.utcnow()
            self.db.commit()

            # Mark as synced today
            self.cache_service.mark_synced_today(str(account.id), "trading")

            logger.info(
                f"Sync completed for account {account.id}: "
                f"{synced_count} succeeded, {failed_count} failed"
            )

            return {
                'account_id': str(account.id),
                'items_synced': synced_count,
                'items_failed': failed_count,
                'sync_time': account.last_sync_at,
                'errors': errors[:10],  # Limit to first 10 errors
                'cached': False
            }

        except Exception as e:
            error_msg = f"Fatal error syncing account {account.id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

            return {
                'account_id': str(account.id),
                'items_synced': synced_count,
                'items_failed': failed_count,
                'sync_time': None,
                'errors': errors,
            }


    def _upsert_listing(self, account: EbayAccount, item_data: Dict[str, Any]) -> Listing:
        """
        Create or update listing record

        Args:
            account: EbayAccount instance
            item_data: Item data from Trading API

        Returns:
            Listing instance
        """
        # Try to find existing listing
        listing = self.db.query(Listing).filter(
            Listing.account_id == account.id,
            Listing.item_id == item_data['item_id']
        ).first()

        if not listing:
            # Create new listing
            listing = Listing(
                account_id=account.id,
                item_id=item_data['item_id'],
            )
            self.db.add(listing)
            logger.debug(f"Created new listing: {item_data['item_id']}")
        else:
            logger.debug(f"Updating existing listing: {item_data['item_id']}")

        # Update fields
        listing.title = item_data['title']
        listing.price = item_data['current_price']
        listing.currency = item_data['currency']
        listing.category_id = item_data['category_id']
        listing.category_name = item_data['category_name']
        listing.image_url = item_data['image_url']
        listing.listing_type = item_data['listing_type']
        listing.listing_status = item_data['listing_status']
        listing.quantity = item_data['quantity']
        listing.quantity_sold = item_data['quantity_sold']
        listing.is_active = (item_data['listing_status'] == 'Active')

        # Parse timestamps if present
        if item_data.get('start_time'):
            try:
                listing.start_time = datetime.fromisoformat(
                    item_data['start_time'].replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

        if item_data.get('end_time'):
            try:
                listing.end_time = datetime.fromisoformat(
                    item_data['end_time'].replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

        try:
            self.db.commit()
        except IntegrityError as e:
            logger.error(f"Integrity error upserting listing {item_data['item_id']}: {e}")
            self.db.rollback()
            raise

        return listing

    def _insert_daily_metric(self, listing: Listing, item_data: Dict[str, Any]):
        """
        Insert or update daily metric record

        Args:
            listing: Listing instance
            item_data: Item data from Trading API
        """
        today = date.today()

        # Check if metric already exists for today
        existing = self.db.query(DailyMetric).filter(
            DailyMetric.listing_id == listing.id,
            DailyMetric.recorded_date == today
        ).first()

        if existing:
            # Update existing (in case of re-sync)
            existing.view_count = item_data['view_count']
            existing.watch_count = item_data['watch_count']
            existing.bid_count = item_data['bid_count']
            existing.current_price = item_data['current_price']
            logger.debug(f"Updated daily metric for listing {listing.item_id}")
        else:
            # Insert new
            metric = DailyMetric(
                listing_id=listing.id,
                recorded_date=today,
                view_count=item_data['view_count'],
                watch_count=item_data['watch_count'],
                bid_count=item_data['bid_count'],
                current_price=item_data['current_price'],
            )
            self.db.add(metric)
            logger.debug(f"Created daily metric for listing {listing.item_id}")

        try:
            self.db.commit()
        except IntegrityError as e:
            logger.error(f"Integrity error inserting metric for listing {listing.item_id}: {e}")
            self.db.rollback()
            raise

    async def sync_all_active_accounts(self) -> List[Dict[str, Any]]:
        """
        Sync all active eBay accounts

        Returns:
            List of sync results for each account
        """
        # Use joinedload to prevent N+1 queries
        accounts = self.db.query(EbayAccount).options(
            joinedload(EbayAccount.oauth_credential),
            joinedload(EbayAccount.tenant)
        ).filter(
            EbayAccount.is_active == True
        ).all()

        logger.info(f"Starting sync for {len(accounts)} active accounts")

        results = []
        for account in accounts:
            try:
                result = await self.sync_account_listings(account)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync account {account.id}: {e}", exc_info=True)
                results.append({
                    'account_id': str(account.id),
                    'items_synced': 0,
                    'items_failed': 0,
                    'sync_time': None,
                    'errors': [str(e)],
                })

        logger.info(
            f"Completed sync for all accounts. "
            f"Total synced: {sum(r['items_synced'] for r in results)}"
        )

        return results
