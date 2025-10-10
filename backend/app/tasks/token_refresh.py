"""
Token Refresh Task
Scheduled task to refresh expiring OAuth tokens
"""
import logging
from datetime import datetime, timedelta
from app.celery_app import celery
from app.database import SessionLocal
from app.models import OAuthCredential
from app.services.ebay_oauth_service import EbayOAuthService

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, name='app.tasks.token_refresh.refresh_expiring_tokens')
def refresh_expiring_tokens(self):
    """
    Refresh OAuth tokens that are expiring within 2 hours
    Scheduled to run every hour

    Returns:
        dict: Summary of refresh results
    """
    db = SessionLocal()

    try:
        logger.info("Starting token refresh task")

        oauth_service = EbayOAuthService()

        # Find tokens expiring in the next 2 hours
        expiry_threshold = datetime.utcnow() + timedelta(hours=2)

        credentials = db.query(OAuthCredential).filter(
            OAuthCredential.is_valid == True,
            OAuthCredential.access_token_expires_at <= expiry_threshold
        ).all()

        logger.info(f"Found {len(credentials)} tokens to refresh")

        refreshed_count = 0
        failed_count = 0
        errors = []

        for credential in credentials:
            try:
                # Refresh the token
                import asyncio
                asyncio.run(oauth_service.refresh_access_token(db, credential))

                refreshed_count += 1
                logger.info(f"Refreshed token for tenant {credential.tenant_id}")

            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to refresh token for tenant {credential.tenant_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with other tokens

        summary = {
            'status': 'success',
            'tokens_refreshed': refreshed_count,
            'tokens_failed': failed_count,
            'errors': errors[:10],  # Limit to first 10 errors
        }

        logger.info(
            f"Token refresh completed: {refreshed_count} refreshed, {failed_count} failed"
        )

        return summary

    except Exception as exc:
        logger.error(f"Token refresh task failed: {exc}", exc_info=True)

        # Retry after 10 minutes
        raise self.retry(exc=exc, countdown=600)

    finally:
        db.close()
