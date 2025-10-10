"""
Analytics Sync Celery Tasks

Analytics APIからトラフィックデータを定期的に取得
"""
import logging
from datetime import date
from app.celery_app import celery
from app.database import SessionLocal
from app.services.analytics_sync_service import AnalyticsSyncService

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    max_retries=3,
    name='app.tasks.analytics_sync.sync_all_analytics'
)
def sync_all_analytics(self, recorded_date: str = None):
    """
    全アカウントのAnalyticsデータを同期（Celery Beatから自動実行）

    Args:
        recorded_date: 記録日（YYYY-MM-DD形式、未指定の場合は今日）

    Returns:
        dict: 同期結果
    """
    db = SessionLocal()
    try:
        # 記録日を決定
        if recorded_date:
            target_date = date.fromisoformat(recorded_date)
        else:
            target_date = date.today()

        logger.info(f"Starting analytics sync for all accounts on {target_date}")

        # Analytics同期サービスを実行
        service = AnalyticsSyncService(db)
        import asyncio
        result = asyncio.run(service.sync_all_accounts_analytics(target_date))

        logger.info(
            f"Analytics sync completed: {result['total_accounts']} accounts, "
            f"{result['total_synced']} listings"
        )

        return {
            'status': 'success',
            'total_accounts': result['total_accounts'],
            'total_synced': result['total_synced'],
            'recorded_date': str(target_date),
            'accounts_processed': result['accounts_processed']
        }

    except Exception as exc:
        logger.error(f"Analytics sync failed: {exc}", exc_info=True)
        # 5分後にリトライ
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


@celery.task(
    bind=True,
    max_retries=3,
    name='app.tasks.analytics_sync.sync_single_account_analytics'
)
def sync_single_account_analytics(self, account_id: str, recorded_date: str = None):
    """
    特定アカウントのAnalyticsデータを同期（手動トリガー用）

    Args:
        account_id: eBayアカウントID（UUID文字列）
        recorded_date: 記録日（YYYY-MM-DD形式、未指定の場合は今日）

    Returns:
        dict: 同期結果
    """
    db = SessionLocal()
    try:
        from app.models.ebay_account import EbayAccount

        # 記録日を決定
        if recorded_date:
            target_date = date.fromisoformat(recorded_date)
        else:
            target_date = date.today()

        logger.info(f"Starting analytics sync for account {account_id} on {target_date}")

        # アカウントを取得
        account = db.query(EbayAccount).filter(EbayAccount.id == account_id).first()
        if not account:
            raise Exception(f"Account {account_id} not found")

        # Analytics同期サービスを実行
        service = AnalyticsSyncService(db)
        import asyncio
        result = asyncio.run(service.sync_account_analytics(account, target_date))

        logger.info(f"Account {account_id}: synced {result['synced']} listings")

        return {
            'status': 'success',
            'account_id': account_id,
            'synced': result['synced'],
            'recorded_date': str(target_date)
        }

    except Exception as exc:
        logger.error(f"Analytics sync failed for account {account_id}: {exc}", exc_info=True)
        # 5分後にリトライ
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()
