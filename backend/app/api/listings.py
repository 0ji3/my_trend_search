"""
Listings API Endpoints
Endpoints for viewing eBay listings and their metrics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Tenant, Listing, DailyMetric, EbayAccount
from app.api.auth import get_current_tenant
from app.schemas.sync import ListingResponse, ListingsListResponse, DailyMetricResponse

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("/", response_model=ListingsListResponse)
def get_listings(
    account_id: Optional[str] = None,
    is_active: Optional[bool] = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get list of listings

    Filters:
    - account_id: Filter by specific eBay account
    - is_active: Filter by active/inactive status
    - page: Page number (1-indexed)
    - page_size: Items per page (max 200)

    Returns paginated list of listings
    """
    # Build query
    query = db.query(Listing).join(EbayAccount).filter(
        EbayAccount.tenant_id == current_tenant.id
    )

    if account_id:
        # Verify account belongs to tenant
        account = db.query(EbayAccount).filter(
            EbayAccount.id == account_id,
            EbayAccount.tenant_id == current_tenant.id
        ).first()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="eBay account not found"
            )

        query = query.filter(Listing.account_id == account_id)

    if is_active is not None:
        query = query.filter(Listing.is_active == is_active)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    listings = query.order_by(Listing.updated_at.desc()).offset(offset).limit(page_size).all()

    return ListingsListResponse(
        listings=[ListingResponse.model_validate(listing) for listing in listings],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(
    listing_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific listing
    """
    listing = db.query(Listing).join(EbayAccount).filter(
        Listing.id == listing_id,
        EbayAccount.tenant_id == current_tenant.id
    ).first()

    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )

    return ListingResponse.model_validate(listing)


@router.get("/{listing_id}/metrics", response_model=dict)
def get_listing_metrics(
    listing_id: str,
    days: int = Query(30, ge=1, le=90),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get daily metrics history for a listing

    Returns time-series data for views, watches, bids, and price
    """
    # Verify listing belongs to tenant
    listing = db.query(Listing).join(EbayAccount).filter(
        Listing.id == listing_id,
        EbayAccount.tenant_id == current_tenant.id
    ).first()

    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )

    # Get metrics for specified days
    metrics = db.query(DailyMetric).filter(
        DailyMetric.listing_id == listing_id
    ).order_by(DailyMetric.recorded_date.desc()).limit(days).all()

    # Reverse to get chronological order
    metrics.reverse()

    return {
        'listing_id': listing_id,
        'item_id': listing.item_id,
        'title': listing.title,
        'metrics': [DailyMetricResponse.model_validate(m) for m in metrics],
        'total_metrics': len(metrics),
    }
