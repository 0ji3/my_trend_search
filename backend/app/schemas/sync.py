"""
Sync Schemas
Pydantic models for data synchronization endpoints
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SyncTriggerRequest(BaseModel):
    """Request to trigger manual sync"""
    account_id: Optional[str] = None  # If None, sync all accounts


class SyncAccountResult(BaseModel):
    """Result for a single account sync"""
    account_id: str
    items_synced: int
    items_failed: int
    sync_time: Optional[datetime] = None
    errors: List[str] = []


class SyncTriggerResponse(BaseModel):
    """Response after triggering sync"""
    status: str
    message: str
    task_id: str  # Celery task ID
    accounts_to_sync: int


class SyncStatusResponse(BaseModel):
    """Response for sync status query"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    result: Optional[dict] = None
    error: Optional[str] = None
    progress: Optional[int] = None  # Percentage 0-100


class ListingResponse(BaseModel):
    """Listing details response"""
    id: str
    account_id: str
    item_id: str
    title: str
    price: Optional[float] = None
    currency: str = "USD"
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    is_active: bool
    image_url: Optional[str] = None
    listing_type: Optional[str] = None
    listing_status: Optional[str] = None
    quantity: Optional[int] = None
    quantity_sold: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyMetricResponse(BaseModel):
    """Daily metric response"""
    id: str
    listing_id: str
    recorded_date: str  # ISO date string
    view_count: int
    watch_count: int
    bid_count: int
    current_price: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ListingsListResponse(BaseModel):
    """List of listings with pagination"""
    listings: List[ListingResponse]
    total: int
    page: int
    page_size: int
