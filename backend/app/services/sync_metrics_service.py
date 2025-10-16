"""
Sync Metrics Service

同期統計の記録と取得
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


class SyncMetricsService:
    """
    同期メトリクスサービス

    同期タスクの成功/失敗率、所要時間、API呼び出し数などを記録・分析
    """

    def __init__(self, db: Session):
        self.db = db

    def record_sync(
        self,
        account_id: str,
        sync_type: str,
        status: str,
        items_synced: int = 0,
        items_failed: int = 0,
        duration_seconds: float = 0.0,
        api_calls: int = 0,
        errors: List[str] = None
    ):
        """
        同期結果を記録

        Args:
            account_id: アカウントID
            sync_type: 同期タイプ（"trading", "analytics", "feed"）
            status: ステータス（"success", "partial", "failed"）
            items_synced: 同期成功件数
            items_failed: 同期失敗件数
            duration_seconds: 所要時間（秒）
            api_calls: API呼び出し数
            errors: エラーメッセージリスト
        """
        try:
            sync_log = SyncLog(
                account_id=account_id,
                sync_type=sync_type,
                status=status,
                items_synced=items_synced,
                items_failed=items_failed,
                duration_seconds=duration_seconds,
                api_calls=api_calls,
                errors=errors or [],
                synced_at=datetime.utcnow()
            )

            self.db.add(sync_log)
            self.db.commit()

            logger.info(
                f"Recorded sync: {sync_type} for account {account_id} - "
                f"Status: {status}, Synced: {items_synced}, Failed: {items_failed}"
            )

        except Exception as e:
            logger.error(f"Failed to record sync metrics: {e}")
            self.db.rollback()

    def get_sync_history(
        self,
        account_id: Optional[str] = None,
        sync_type: Optional[str] = None,
        days: int = 7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        同期履歴を取得

        Args:
            account_id: アカウントID（Noneの場合は全アカウント）
            sync_type: 同期タイプ（Noneの場合は全タイプ）
            days: 過去何日分取得するか
            limit: 最大取得件数

        Returns:
            同期履歴のリスト
        """
        try:
            query = self.db.query(SyncLog)

            # Filter by account
            if account_id:
                query = query.filter(SyncLog.account_id == account_id)

            # Filter by sync type
            if sync_type:
                query = query.filter(SyncLog.sync_type == sync_type)

            # Filter by date range
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(SyncLog.synced_at >= start_date)

            # Order and limit
            logs = query.order_by(desc(SyncLog.synced_at)).limit(limit).all()

            return [
                {
                    'id': str(log.id),
                    'account_id': str(log.account_id),
                    'sync_type': log.sync_type,
                    'status': log.status,
                    'items_synced': log.items_synced,
                    'items_failed': log.items_failed,
                    'duration_seconds': log.duration_seconds,
                    'api_calls': log.api_calls,
                    'errors': log.errors,
                    'synced_at': log.synced_at.isoformat()
                }
                for log in logs
            ]

        except Exception as e:
            logger.error(f"Failed to get sync history: {e}")
            return []

    def get_sync_statistics(
        self,
        account_id: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        同期統計を取得

        Args:
            account_id: アカウントID（Noneの場合は全アカウント）
            days: 過去何日分の統計か

        Returns:
            統計情報
        """
        try:
            query = self.db.query(SyncLog)

            if account_id:
                query = query.filter(SyncLog.account_id == account_id)

            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(SyncLog.synced_at >= start_date)

            logs = query.all()

            if not logs:
                return {
                    'total_syncs': 0,
                    'successful_syncs': 0,
                    'failed_syncs': 0,
                    'success_rate': 0.0,
                    'total_items_synced': 0,
                    'total_items_failed': 0,
                    'avg_duration_seconds': 0.0,
                    'total_api_calls': 0,
                    'period_days': days
                }

            successful = sum(1 for log in logs if log.status == 'success')
            failed = sum(1 for log in logs if log.status == 'failed')
            total = len(logs)

            return {
                'total_syncs': total,
                'successful_syncs': successful,
                'failed_syncs': failed,
                'success_rate': (successful / total * 100) if total > 0 else 0.0,
                'total_items_synced': sum(log.items_synced for log in logs),
                'total_items_failed': sum(log.items_failed for log in logs),
                'avg_duration_seconds': sum(log.duration_seconds for log in logs) / total,
                'total_api_calls': sum(log.api_calls for log in logs),
                'period_days': days,
                'by_type': self._get_stats_by_type(logs)
            }

        except Exception as e:
            logger.error(f"Failed to get sync statistics: {e}")
            return {}

    def _get_stats_by_type(self, logs: List[SyncLog]) -> Dict[str, Dict[str, Any]]:
        """
        タイプ別の統計を取得

        Args:
            logs: SyncLogのリスト

        Returns:
            タイプ別統計
        """
        stats_by_type = {}

        for sync_type in ['trading', 'analytics', 'feed']:
            type_logs = [log for log in logs if log.sync_type == sync_type]

            if not type_logs:
                continue

            successful = sum(1 for log in type_logs if log.status == 'success')
            total = len(type_logs)

            stats_by_type[sync_type] = {
                'total_syncs': total,
                'successful_syncs': successful,
                'success_rate': (successful / total * 100) if total > 0 else 0.0,
                'total_items_synced': sum(log.items_synced for log in type_logs),
                'avg_duration_seconds': sum(log.duration_seconds for log in type_logs) / total,
                'total_api_calls': sum(log.api_calls for log in type_logs)
            }

        return stats_by_type

    def get_recent_errors(
        self,
        account_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        最近のエラーを取得

        Args:
            account_id: アカウントID（Noneの場合は全アカウント）
            limit: 最大取得件数

        Returns:
            エラー情報のリスト
        """
        try:
            query = self.db.query(SyncLog).filter(
                SyncLog.status.in_(['failed', 'partial'])
            )

            if account_id:
                query = query.filter(SyncLog.account_id == account_id)

            logs = query.order_by(desc(SyncLog.synced_at)).limit(limit).all()

            return [
                {
                    'id': str(log.id),
                    'account_id': str(log.account_id),
                    'sync_type': log.sync_type,
                    'status': log.status,
                    'errors': log.errors,
                    'synced_at': log.synced_at.isoformat()
                }
                for log in logs if log.errors
            ]

        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []
