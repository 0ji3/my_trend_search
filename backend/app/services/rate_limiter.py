"""
eBay API Rate Limiter Service

Tracks API call counts to prevent exceeding eBay's rate limits
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import redis
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    eBay API rate limiting handler

    eBay API Limits (Standard Account):
    - 5,000 calls per day (24-hour period)
    - Resets at midnight UTC

    Uses Redis to track API call counts per tenant/account
    """

    def __init__(self):
        # Connect to Redis
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )

        # Default limits
        self.daily_limit = 5000  # eBay standard limit
        self.warning_threshold = 4500  # 90% of limit

    def _get_key(self, tenant_id: str, api_type: str = "all") -> str:
        """
        Generate Redis key for rate limit tracking

        Args:
            tenant_id: Tenant UUID
            api_type: API type (trading, analytics, feed, or "all")

        Returns:
            Redis key string
        """
        today = datetime.utcnow().date()
        return f"rate_limit:{tenant_id}:{api_type}:{today}"

    def check_rate_limit(
        self,
        tenant_id: str,
        api_type: str = "all",
        required_calls: int = 1
    ) -> bool:
        """
        Check if API call is allowed within rate limit

        Args:
            tenant_id: Tenant UUID
            api_type: API type (trading, analytics, feed, or "all")
            required_calls: Number of calls needed

        Returns:
            True if allowed, False if rate limit would be exceeded
        """
        key = self._get_key(tenant_id, api_type)

        try:
            current_count = int(self.redis_client.get(key) or 0)

            if current_count + required_calls > self.daily_limit:
                logger.warning(
                    f"Rate limit check failed for {tenant_id}: "
                    f"current={current_count}, required={required_calls}, limit={self.daily_limit}"
                )
                return False

            # Check if approaching limit
            if current_count + required_calls > self.warning_threshold:
                logger.warning(
                    f"Approaching rate limit for {tenant_id}: "
                    f"{current_count + required_calls}/{self.daily_limit} calls"
                )

            return True

        except redis.RedisError as e:
            logger.error(f"Redis error checking rate limit: {e}")
            # Fail open: allow the call if Redis is down
            return True

    def record_api_call(
        self,
        tenant_id: str,
        api_type: str = "all",
        call_count: int = 1
    ):
        """
        Record API call(s) in Redis

        Args:
            tenant_id: Tenant UUID
            api_type: API type (trading, analytics, feed, or "all")
            call_count: Number of calls made
        """
        key = self._get_key(tenant_id, api_type)

        try:
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(key, call_count)

            # Set expiration to end of day (UTC)
            now = datetime.utcnow()
            midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
            ttl = int((midnight - now).total_seconds())
            pipe.expire(key, ttl)

            pipe.execute()

            logger.debug(f"Recorded {call_count} API calls for {tenant_id} ({api_type})")

        except redis.RedisError as e:
            logger.error(f"Redis error recording API call: {e}")
            # Don't fail the operation if Redis is down

    def get_remaining_calls(
        self,
        tenant_id: str,
        api_type: str = "all"
    ) -> dict:
        """
        Get remaining API calls for tenant

        Args:
            tenant_id: Tenant UUID
            api_type: API type (trading, analytics, feed, or "all")

        Returns:
            dict: {
                'used': int,
                'remaining': int,
                'limit': int,
                'reset_at': datetime
            }
        """
        key = self._get_key(tenant_id, api_type)

        try:
            used = int(self.redis_client.get(key) or 0)
            remaining = max(0, self.daily_limit - used)

            # Calculate reset time (midnight UTC)
            now = datetime.utcnow()
            reset_at = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())

            return {
                'used': used,
                'remaining': remaining,
                'limit': self.daily_limit,
                'reset_at': reset_at
            }

        except redis.RedisError as e:
            logger.error(f"Redis error getting remaining calls: {e}")
            return {
                'used': 0,
                'remaining': self.daily_limit,
                'limit': self.daily_limit,
                'reset_at': None
            }

    def reset_counter(self, tenant_id: str, api_type: str = "all"):
        """
        Manually reset counter (for testing or emergency)

        Args:
            tenant_id: Tenant UUID
            api_type: API type (trading, analytics, feed, or "all")
        """
        key = self._get_key(tenant_id, api_type)

        try:
            self.redis_client.delete(key)
            logger.info(f"Reset rate limit counter for {tenant_id} ({api_type})")

        except redis.RedisError as e:
            logger.error(f"Redis error resetting counter: {e}")
