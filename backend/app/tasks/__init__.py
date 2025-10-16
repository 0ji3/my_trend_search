"""
Celery Tasks Package

Import all task modules to register them with Celery
"""

# Import all task modules to register them with Celery
from app.tasks import daily_sync
from app.tasks import analytics_sync
from app.tasks import trend_analysis
from app.tasks import token_refresh
from app.tasks import feed_sync

__all__ = [
    'daily_sync',
    'analytics_sync',
    'trend_analysis',
    'token_refresh',
    'feed_sync',
]
