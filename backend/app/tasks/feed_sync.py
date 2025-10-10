"""
Feed Sync Celery Tasks

Feed APIを使った一括同期（初回同期向け）
"""
import logging
from app.celery_app import celery
from app.database import SessionLocal
from app.services.feed_sync_service import FeedSyncService

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    max_retries=3,
    name='app.tasks.feed_sync.bulk_sync_all_accounts'
)
def bulk_sync_all_accounts(self):
    """
    全アカウントをFeed APIで一括同期（手動トリガー用）

    Returns:
        dict: 同期結果
    """
    db = SessionLocal()
    try:
        logger.info("Starting bulk sync for all accounts using Feed API")

        # Feed同期サービスを実行
        service = FeedSyncService(db)
        import asyncio
        result = asyncio.run(service.bulk_sync_all_accounts())

        logger.info(
            f"Bulk sync completed: {result['total_accounts']} accounts, "
            f"{result['total_synced']} listings"
        )

        return {
            'status': 'success',
            'total_accounts': result['total_accounts'],
            'total_synced': result['total_synced'],
            'accounts_processed': result['accounts_processed']
        }

    except Exception as exc:
        logger.error(f"Bulk sync failed: {exc}", exc_info=True)
        # 10分後にリトライ（Feed APIは時間がかかるため）
        raise self.retry(exc=exc, countdown=600)
    finally:
        db.close()


@celery.task(
    bind=True,
    max_retries=3,
    name='app.tasks.feed_sync.bulk_sync_single_account'
)
def bulk_sync_single_account(self, account_id: str):
    """
    特定アカウントをFeed APIで一括同期（手動トリガー用）

    Args:
        account_id: eBayアカウントID（UUID文字列）

    Returns:
        dict: 同期結果
    """
    db = SessionLocal()
    try:
        from app.models.ebay_account import EbayAccount

        logger.info(f"Starting bulk sync for account {account_id} using Feed API")

        # アカウントを取得
        account = db.query(EbayAccount).filter(EbayAccount.id == account_id).first()
        if not account:
            raise Exception(f"Account {account_id} not found")

        # Feed同期サービスを実行
        service = FeedSyncService(db)
        import asyncio
        result = asyncio.run(service.bulk_sync_account(account, wait_for_completion=True))

        if result['status'] == 'completed':
            logger.info(f"Account {account_id}: bulk synced {result['synced']} listings")
        else:
            logger.info(f"Account {account_id}: bulk sync queued")

        return {
            'status': result['status'],
            'account_id': account_id,
            'synced': result.get('synced', 0)
        }

    except Exception as exc:
        logger.error(f"Bulk sync failed for account {account_id}: {exc}", exc_info=True)
        # 10分後にリトライ
        raise self.retry(exc=exc, countdown=600)
    finally:
        db.close()
