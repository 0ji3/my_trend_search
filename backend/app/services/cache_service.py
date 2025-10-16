"""
Cache Service

Redisを使用したキャッシング機能
"""
import logging
import json
from typing import Any, Optional
from datetime import datetime, timedelta
import redis
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redisベースのキャッシングサービス

    用途:
    - API呼び出し結果のキャッシュ
    - 同じ日の重複データ取得防止
    - パフォーマンス向上
    """

    def __init__(self):
        # Connect to Redis
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )

        # Default TTL (Time To Live)
        self.default_ttl = 86400  # 24時間

    def _get_key(self, prefix: str, identifier: str) -> str:
        """
        Redisキーを生成

        Args:
            prefix: キープレフィックス（例: "listing", "analytics"）
            identifier: 識別子（例: "account_id:date"）

        Returns:
            Redisキー文字列
        """
        return f"cache:{prefix}:{identifier}"

    def get(self, prefix: str, identifier: str) -> Optional[Any]:
        """
        キャッシュから値を取得

        Args:
            prefix: キープレフィックス
            identifier: 識別子

        Returns:
            キャッシュされた値、または None
        """
        key = self._get_key(prefix, identifier)

        try:
            value = self.redis_client.get(key)

            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss: {key}")
                return None

        except redis.RedisError as e:
            logger.error(f"Redis error getting cache: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None

    def set(
        self,
        prefix: str,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """
        キャッシュに値を保存

        Args:
            prefix: キープレフィックス
            identifier: 識別子
            value: 保存する値（JSON serializable）
            ttl: Time To Live（秒）、Noneの場合はdefault_ttlを使用
        """
        key = self._get_key(prefix, identifier)

        if ttl is None:
            ttl = self.default_ttl

        try:
            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

        except redis.RedisError as e:
            logger.error(f"Redis error setting cache: {e}")
        except TypeError as e:
            logger.error(f"JSON serialization error: {e}")

    def delete(self, prefix: str, identifier: str):
        """
        キャッシュから値を削除

        Args:
            prefix: キープレフィックス
            identifier: 識別子
        """
        key = self._get_key(prefix, identifier)

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache deleted: {key}")

        except redis.RedisError as e:
            logger.error(f"Redis error deleting cache: {e}")

    def exists(self, prefix: str, identifier: str) -> bool:
        """
        キャッシュが存在するか確認

        Args:
            prefix: キープレフィックス
            identifier: 識別子

        Returns:
            True if exists, False otherwise
        """
        key = self._get_key(prefix, identifier)

        try:
            return bool(self.redis_client.exists(key))

        except redis.RedisError as e:
            logger.error(f"Redis error checking cache existence: {e}")
            return False

    def get_or_set(
        self,
        prefix: str,
        identifier: str,
        callback,
        ttl: Optional[int] = None
    ) -> Any:
        """
        キャッシュから取得、なければcallbackを実行して保存

        Args:
            prefix: キープレフィックス
            identifier: 識別子
            callback: キャッシュミス時に実行する関数
            ttl: Time To Live（秒）

        Returns:
            キャッシュされた値、またはcallbackの結果
        """
        # Try to get from cache
        cached = self.get(prefix, identifier)

        if cached is not None:
            return cached

        # Cache miss, execute callback
        try:
            result = callback()

            # Save to cache
            if result is not None:
                self.set(prefix, identifier, result, ttl)

            return result

        except Exception as e:
            logger.error(f"Error executing callback: {e}")
            raise

    def clear_pattern(self, pattern: str):
        """
        パターンに一致するキーを削除

        Args:
            pattern: パターン（例: "cache:listing:*"）
        """
        try:
            keys = self.redis_client.keys(pattern)

            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries matching pattern: {pattern}")

        except redis.RedisError as e:
            logger.error(f"Redis error clearing pattern: {e}")

    def get_ttl(self, prefix: str, identifier: str) -> Optional[int]:
        """
        キャッシュの残り有効期限を取得

        Args:
            prefix: キープレフィックス
            identifier: 識別子

        Returns:
            残り秒数、またはNone（キャッシュが存在しない場合）
        """
        key = self._get_key(prefix, identifier)

        try:
            ttl = self.redis_client.ttl(key)

            if ttl > 0:
                return ttl
            else:
                return None

        except redis.RedisError as e:
            logger.error(f"Redis error getting TTL: {e}")
            return None

    def is_synced_today(self, account_id: str, sync_type: str) -> bool:
        """
        今日すでに同期済みかチェック

        Args:
            account_id: アカウントID
            sync_type: 同期タイプ（"trading", "analytics", "feed"）

        Returns:
            True if synced today, False otherwise
        """
        today = datetime.utcnow().date()
        identifier = f"{account_id}:{sync_type}:{today}"

        return self.exists("sync_status", identifier)

    def mark_synced_today(self, account_id: str, sync_type: str):
        """
        今日の同期完了をマーク

        Args:
            account_id: アカウントID
            sync_type: 同期タイプ（"trading", "analytics", "feed"）
        """
        today = datetime.utcnow().date()
        identifier = f"{account_id}:{sync_type}:{today}"

        # Mark as synced with timestamp
        self.set(
            "sync_status",
            identifier,
            {"synced_at": datetime.utcnow().isoformat()},
            ttl=86400  # 24時間で自動削除
        )
