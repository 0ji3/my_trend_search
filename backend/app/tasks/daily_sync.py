"""
Daily Sync Task
Scheduled task to sync eBay listing data daily
"""
import logging
from app.celery_app import celery
from app.database import SessionLocal
from app.services.ebay_data_sync_service import EbayDataSyncService
from app.models import EbayAccount

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, name='app.tasks.daily_sync.sync_all_accounts')
def sync_all_accounts(self):
    """
    Sync all active eBay accounts
    Scheduled to run daily at 2 AM UTC

    Returns:
        dict: Summary of sync results
    """
    db = SessionLocal()

    try:
        logger.info("Starting daily sync task for all accounts")

        sync_service = EbayDataSyncService(db)

        # Sync all active accounts
        import asyncio
        results = asyncio.run(sync_service.sync_all_active_accounts())

        # Calculate summary
        total_synced = sum(r['items_synced'] for r in results)
        total_failed = sum(r['items_failed'] for r in results)

        summary = {
            'status': 'success',
            'accounts_processed': len(results),
            'total_items_synced': total_synced,
            'total_items_failed': total_failed,
            'results': results,
        }

        logger.info(
            f"Daily sync completed: {len(results)} accounts, "
            f"{total_synced} items synced, {total_failed} failed"
        )

        return summary

    except Exception as exc:
        logger.error(f"Daily sync task failed: {exc}", exc_info=True)

        # Retry after 5 minutes
        raise self.retry(exc=exc, countdown=300)

    finally:
        db.close()


@celery.task(bind=True, max_retries=3, name='app.tasks.daily_sync.sync_single_account')
def sync_single_account(self, account_id: str):
    """
    Sync a single eBay account
    Can be triggered manually

    Args:
        account_id: UUID of the eBay account

    Returns:
        dict: Sync result for this account
    """
    db = SessionLocal()

    try:
        logger.info(f"Starting manual sync for account {account_id}")

        # Get account
        account = db.query(EbayAccount).filter(EbayAccount.id == account_id).first()

        if not account:
            raise ValueError(f"Account {account_id} not found")

        if not account.is_active:
            raise ValueError(f"Account {account_id} is not active")

        # Sync account
        sync_service = EbayDataSyncService(db)
        import asyncio
        result = asyncio.run(sync_service.sync_account_listings(account))

        logger.info(
            f"Manual sync completed for account {account_id}: "
            f"{result['items_synced']} items synced"
        )

        return result

    except Exception as exc:
        logger.error(f"Manual sync failed for account {account_id}: {exc}", exc_info=True)

        # Retry after 1 minute
        raise self.retry(exc=exc, countdown=60)

    finally:
        db.close()
