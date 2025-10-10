"""
Trend Analysis Celery Tasks

トレンド分析を実行するバックグラウンドタスク
"""
import logging
from datetime import date
from app.celery_app import celery
from app.database import SessionLocal
from app.services.trend_analysis_service import TrendAnalysisService

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    max_retries=3,
    name='app.tasks.trend_analysis.analyze_all_trends'
)
def analyze_all_trends(self, analysis_date: str = None):
    """
    全アカウントのトレンド分析を実行（Celery Beat から毎日自動実行）

    Args:
        analysis_date: 分析対象日（YYYY-MM-DD形式、未指定の場合は今日）

    Returns:
        dict: {
            'status': str,
            'total_accounts': int,
            'total_listings_analyzed': int,
            'analysis_date': str
        }
    """
    db = SessionLocal()
    try:
        # 分析対象日を決定
        if analysis_date:
            target_date = date.fromisoformat(analysis_date)
        else:
            target_date = date.today()

        logger.info(f"Starting trend analysis for all accounts on {target_date}")

        # トレンド分析サービスを実行
        service = TrendAnalysisService(db)
        result = service.analyze_all_accounts(target_date)

        logger.info(
            f"Trend analysis completed: {result['total_accounts']} accounts, "
            f"{result['total_listings_analyzed']} listings"
        )

        return {
            'status': 'success',
            'total_accounts': result['total_accounts'],
            'total_listings_analyzed': result['total_listings_analyzed'],
            'analysis_date': str(target_date),
            'accounts_processed': result['accounts_processed']
        }

    except Exception as exc:
        logger.error(f"Trend analysis failed: {exc}", exc_info=True)
        # 5分後にリトライ
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


@celery.task(
    bind=True,
    max_retries=3,
    name='app.tasks.trend_analysis.analyze_single_account'
)
def analyze_single_account(self, account_id: str, analysis_date: str = None):
    """
    特定アカウントのトレンド分析を実行（手動トリガー用）

    Args:
        account_id: eBayアカウントID（UUID文字列）
        analysis_date: 分析対象日（YYYY-MM-DD形式、未指定の場合は今日）

    Returns:
        dict: {
            'status': str,
            'account_id': str,
            'listings_analyzed': int,
            'analysis_date': str
        }
    """
    db = SessionLocal()
    try:
        # 分析対象日を決定
        if analysis_date:
            target_date = date.fromisoformat(analysis_date)
        else:
            target_date = date.today()

        logger.info(f"Starting trend analysis for account {account_id} on {target_date}")

        # トレンド分析サービスを実行
        service = TrendAnalysisService(db)
        results = service.analyze_account(account_id, target_date)

        logger.info(f"Account {account_id}: analyzed {len(results)} listings")

        return {
            'status': 'success',
            'account_id': account_id,
            'listings_analyzed': len(results),
            'analysis_date': str(target_date)
        }

    except Exception as exc:
        logger.error(f"Trend analysis failed for account {account_id}: {exc}", exc_info=True)
        # 5分後にリトライ
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()
