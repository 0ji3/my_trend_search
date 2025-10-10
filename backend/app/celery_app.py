"""
Celery Application Configuration
Configures Celery for background tasks and scheduled jobs
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Create Celery instance
celery = Celery(
    'ebay_trend_research',
    broker=getattr(settings, 'REDIS_URL', 'redis://redis:6379/0'),
    backend=getattr(settings, 'REDIS_URL', 'redis://redis:6379/0'),
)

# Celery configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks
celery.autodiscover_tasks(['app.tasks'])

# Celery Beat schedule (cron jobs)
celery.conf.beat_schedule = {
    'daily-data-sync': {
        'task': 'app.tasks.daily_sync.sync_all_accounts',
        'schedule': crontab(hour=2, minute=0),  # Every day at 2:00 AM UTC
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        },
    },
    'token-refresh': {
        'task': 'app.tasks.token_refresh.refresh_expiring_tokens',
        'schedule': crontab(minute=0),  # Every hour
        'options': {
            'expires': 1800,  # Task expires after 30 minutes
        },
    },
    # Future tasks can be added here:
    # 'daily-trend-analysis': {
    #     'task': 'app.tasks.trend_analysis.analyze_all_trends',
    #     'schedule': crontab(hour=3, minute=0),  # Every day at 3:00 AM UTC
    # },
}

@celery.task(bind=True)
def debug_task(self):
    """Test task for debugging"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'
