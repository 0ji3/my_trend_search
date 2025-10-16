"""
Sync Log Model

同期ログを記録するモデル
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.database import Base


class SyncLog(Base):
    """
    同期ログモデル

    各同期タスクの実行結果を記録
    """
    __tablename__ = "sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    sync_type = Column(String(50), nullable=False)  # 'trading', 'analytics', 'feed'
    status = Column(String(20), nullable=False)  # 'success', 'partial', 'failed'
    items_synced = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    api_calls = Column(Integer, default=0)
    errors = Column(JSON, default=list)  # List of error messages
    synced_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_sync_logs_account_type', 'account_id', 'sync_type'),
        Index('idx_sync_logs_synced_at', 'synced_at'),
        Index('idx_sync_logs_status', 'status'),
    )

    def __repr__(self):
        return (
            f"<SyncLog(id={self.id}, account_id={self.account_id}, "
            f"sync_type={self.sync_type}, status={self.status})>"
        )

    def to_dict(self):
        return {
            'id': str(self.id),
            'account_id': str(self.account_id),
            'sync_type': self.sync_type,
            'status': self.status,
            'items_synced': self.items_synced,
            'items_failed': self.items_failed,
            'duration_seconds': self.duration_seconds,
            'api_calls': self.api_calls,
            'errors': self.errors,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }
