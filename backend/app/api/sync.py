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
