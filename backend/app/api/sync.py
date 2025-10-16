"""
Sync API Endpoints
Endpoints for triggering and monitoring data synchronization
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from app.database import get_db
from app.models import Tenant, EbayAccount
from app.api.auth import get_current_tenant
from app.schemas.sync import (
    SyncTriggerRequest,
    SyncTriggerResponse,
    SyncStatusResponse,
)
from app.tasks.daily_sync import sync_all_accounts, sync_single_account
from app.tasks.analytics_sync import sync_all_analytics, sync_single_account_analytics
from app.celery_app import celery

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/trigger", response_model=SyncTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_sync(
    request: SyncTriggerRequest = SyncTriggerRequest(),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Trigger manual data synchronization

    - If account_id is provided, sync only that account
    - If account_id is None, sync all active accounts for the current tenant

    Returns task_id for status monitoring
    """
    if request.account_id:
        # Verify account belongs to current tenant
        account = db.query(EbayAccount).filter(
            EbayAccount.id == request.account_id,
            EbayAccount.tenant_id == current_tenant.id
        ).first()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="eBay account not found"
            )

        if not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="eBay account is not active"
            )

        # Trigger single account sync
        task = sync_single_account.delay(str(account.id))

        return SyncTriggerResponse(
            status="accepted",
            message=f"Sync triggered for account {account.ebay_user_id}",
            task_id=task.id,
            accounts_to_sync=1
        )

    else:
        # Count active accounts for this tenant
        account_count = db.query(EbayAccount).filter(
            EbayAccount.tenant_id == current_tenant.id,
            EbayAccount.is_active == True
        ).count()

        if account_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active eBay accounts found"
            )

        # Trigger sync for all accounts
        # Note: This will sync ALL accounts in the system, not just this tenant's
        # For tenant-specific sync, we would need a separate task
        task = sync_all_accounts.delay()

        return SyncTriggerResponse(
            status="accepted",
            message="Sync triggered for all active accounts",
            task_id=task.id,
            accounts_to_sync=account_count
        )


@router.get("/status/{task_id}", response_model=SyncStatusResponse)
def get_sync_status(
    task_id: str,
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """
    Get status of a sync task

    Task states:
    - PENDING: Task is waiting to be executed
    - STARTED: Task has started
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed
    - RETRY: Task is being retried
    """
    task_result = AsyncResult(task_id, app=celery)

    response = SyncStatusResponse(
        task_id=task_id,
        status=task_result.state,
        result=None,
        error=None,
        progress=None
    )

    if task_result.state == 'PENDING':
        response.result = {'message': 'Task is waiting to be executed'}

    elif task_result.state == 'STARTED':
        response.result = {'message': 'Task is running'}
        response.progress = 50  # Assume 50% when started

    elif task_result.state == 'SUCCESS':
        response.result = task_result.result
        response.progress = 100

    elif task_result.state == 'FAILURE':
        response.error = str(task_result.info)
        response.progress = 0

    elif task_result.state == 'RETRY':
        response.result = {'message': 'Task is being retried'}
        response.progress = 25

    return response


@router.get("/history", response_model=dict)
def get_sync_history(
    limit: int = 10,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get recent sync history for current tenant's accounts

    Returns last sync times and statistics
    """
    accounts = db.query(EbayAccount).filter(
        EbayAccount.tenant_id == current_tenant.id
    ).order_by(EbayAccount.last_sync_at.desc()).limit(limit).all()

    history = []
    for account in accounts:
        # Count listings for this account
        from app.models import Listing
        listing_count = db.query(Listing).filter(
            Listing.account_id == account.id,
            Listing.is_active == True
        ).count()

        history.append({
            'account_id': str(account.id),
            'ebay_user_id': account.ebay_user_id,
            'username': account.username,
            'last_sync_at': account.last_sync_at.isoformat() if account.last_sync_at else None,
            'active_listings': listing_count,
        })

    return {
        'accounts': history,
        'total': len(history),
    }


@router.post("/trading", response_model=SyncTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_trading_sync(
    account_id: str = None,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Trigger Trading API data synchronization

    Fetches listing data with View/Watch counts from Trading API

    - If account_id is provided, sync only that account
    - If account_id is None, sync all active accounts for the current tenant

    Returns task_id for status monitoring
    """
    if account_id:
        # Verify account belongs to current tenant
        account = db.query(EbayAccount).filter(
            EbayAccount.id == account_id,
            EbayAccount.tenant_id == current_tenant.id
        ).first()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="eBay account not found"
            )

        # Trigger single account sync
        task = sync_single_account.delay(str(account.id))

        return SyncTriggerResponse(
            status="accepted",
            message=f"Trading sync triggered for account {account.ebay_user_id}",
            task_id=task.id,
            accounts_to_sync=1
        )

    else:
        # Count active accounts for this tenant
        account_count = db.query(EbayAccount).filter(
            EbayAccount.tenant_id == current_tenant.id,
            EbayAccount.is_active == True
        ).count()

        if account_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active eBay accounts found"
            )

        # Trigger sync for all accounts
        task = sync_all_accounts.delay()

        return SyncTriggerResponse(
            status="accepted",
            message="Trading sync triggered for all active accounts",
            task_id=task.id,
            accounts_to_sync=account_count
        )


@router.post("/analytics", response_model=SyncTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_analytics_sync(
    account_id: str = None,
    recorded_date: str = None,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Trigger Analytics API data synchronization

    Fetches traffic report with CTR, Impressions, Conversion Rate from Analytics API

    - If account_id is provided, sync only that account
    - If account_id is None, sync all active accounts for the current tenant
    - recorded_date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns task_id for status monitoring
    """
    if account_id:
        # Verify account belongs to current tenant
        account = db.query(EbayAccount).filter(
            EbayAccount.id == account_id,
            EbayAccount.tenant_id == current_tenant.id
        ).first()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="eBay account not found"
            )

        # Trigger single account analytics sync
        task = sync_single_account_analytics.delay(str(account.id), recorded_date)

        return SyncTriggerResponse(
            status="accepted",
            message=f"Analytics sync triggered for account {account.ebay_user_id}",
            task_id=task.id,
            accounts_to_sync=1
        )

    else:
        # Count active accounts for this tenant
        account_count = db.query(EbayAccount).filter(
            EbayAccount.tenant_id == current_tenant.id,
            EbayAccount.is_active == True
        ).count()

        if account_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active eBay accounts found"
            )

        # Trigger analytics sync for all accounts
        task = sync_all_analytics.delay(recorded_date)

        return SyncTriggerResponse(
            status="accepted",
            message="Analytics sync triggered for all active accounts",
            task_id=task.id,
            accounts_to_sync=account_count
        )


@router.get("/rate-limit", response_model=dict)
def get_rate_limit_status(
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """
    Get current rate limit status for tenant

    Shows API call usage and remaining calls for the day

    Returns:
        dict: Rate limit information (used, remaining, limit, reset_at)
    """
    from app.services.rate_limiter import RateLimiter

    rate_limiter = RateLimiter()

    # Get rate limits for different API types
    all_apis = rate_limiter.get_remaining_calls(str(current_tenant.id), "all")
    trading = rate_limiter.get_remaining_calls(str(current_tenant.id), "trading")
    analytics = rate_limiter.get_remaining_calls(str(current_tenant.id), "analytics")

    return {
        "all_apis": all_apis,
        "trading": trading,
        "analytics": analytics,
        "tenant_id": str(current_tenant.id)
    }


@router.get("/metrics/statistics", response_model=dict)
def get_sync_statistics(
    days: int = 7,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get sync statistics for tenant

    Shows success/failure rates, average duration, API calls, etc.

    Args:
        days: Number of days to analyze (default: 7)

    Returns:
        dict: Sync statistics
    """
    from app.services.sync_metrics_service import SyncMetricsService

    # Get all accounts for this tenant
    accounts = db.query(EbayAccount).filter(
        EbayAccount.tenant_id == current_tenant.id
    ).all()

    if not accounts:
        return {
            "message": "No accounts found",
            "statistics": {}
        }

    metrics_service = SyncMetricsService(db)

    # Get combined statistics for all accounts
    all_stats = []
    for account in accounts:
        stats = metrics_service.get_sync_statistics(str(account.id), days)
        if stats:
            stats['account_id'] = str(account.id)
            stats['ebay_user_id'] = account.ebay_user_id
            all_stats.append(stats)

    # Calculate overall statistics
    if all_stats:
        total_syncs = sum(s['total_syncs'] for s in all_stats)
        successful_syncs = sum(s['successful_syncs'] for s in all_stats)
        total_items_synced = sum(s['total_items_synced'] for s in all_stats)
        total_api_calls = sum(s['total_api_calls'] for s in all_stats)

        overall = {
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'success_rate': (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0.0,
            'total_items_synced': total_items_synced,
            'total_api_calls': total_api_calls,
            'period_days': days,
            'accounts_count': len(accounts)
        }
    else:
        overall = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'success_rate': 0.0,
            'total_items_synced': 0,
            'total_api_calls': 0,
            'period_days': days,
            'accounts_count': len(accounts)
        }

    return {
        'overall': overall,
        'by_account': all_stats
    }


@router.get("/metrics/errors", response_model=dict)
def get_recent_errors(
    limit: int = 20,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get recent sync errors for tenant

    Shows failed/partial sync attempts with error messages

    Args:
        limit: Maximum number of errors to return (default: 20)

    Returns:
        dict: Recent errors
    """
    from app.services.sync_metrics_service import SyncMetricsService

    # Get all accounts for this tenant
    accounts = db.query(EbayAccount).filter(
        EbayAccount.tenant_id == current_tenant.id
    ).all()

    if not accounts:
        return {
            "message": "No accounts found",
            "errors": []
        }

    metrics_service = SyncMetricsService(db)

    # Get errors for all accounts
    all_errors = []
    for account in accounts:
        errors = metrics_service.get_recent_errors(str(account.id), limit)
        all_errors.extend(errors)

    # Sort by date (most recent first)
    all_errors.sort(key=lambda x: x['synced_at'], reverse=True)

    return {
        'total_errors': len(all_errors),
        'errors': all_errors[:limit]
    }
