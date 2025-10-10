"""
eBay Accounts API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.schemas.ebay import (
    OAuthAuthorizationURL,
    OAuthCallbackRequest,
    EbayAccountResponse,
    EbayAccountListResponse,
    OAuthStatus,
)
from app.services.ebay_oauth_service import EbayOAuthService
from app.models.tenant import Tenant
from app.models.oauth_credential import OAuthCredential
from app.models.ebay_account import EbayAccount
from app.api.auth import get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/auth-url", response_model=OAuthAuthorizationURL)
def get_authorization_url(
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """
    Generate eBay OAuth authorization URL

    **Returns:**
    - authorization_url: URL to redirect user to eBay login
    - state: State parameter for CSRF protection (store this)
    """
    try:
        oauth_service = EbayOAuthService()
        auth_url, state = oauth_service.generate_authorization_url()

        logger.info(f"Generated authorization URL for tenant: {current_tenant.id}")

        return OAuthAuthorizationURL(
            authorization_url=auth_url,
            state=state
        )
    except Exception as e:
        logger.error(f"Failed to generate authorization URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.post("/callback", status_code=status.HTTP_200_OK)
def oauth_callback(
    callback_data: OAuthCallbackRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from eBay

    **Request Body:**
    - code: Authorization code from eBay
    - state: State parameter for validation (optional)

    **Returns:**
    - Success message with OAuth credential info
    """
    try:
        oauth_service = EbayOAuthService()

        # Exchange code for tokens
        tokens = oauth_service.exchange_code_for_tokens(callback_data.code)

        # Save credentials
        credential = oauth_service.save_oauth_credentials(
            db=db,
            tenant=current_tenant,
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            expires_in=tokens['expires_in'],
            refresh_token_expires_in=tokens['refresh_token_expires_in']
        )

        logger.info(f"OAuth callback successful for tenant: {current_tenant.id}")

        return {
            "message": "eBay account connected successfully",
            "credential_id": str(credential.id),
            "expires_at": credential.access_token_expires_at.isoformat()
        }

    except ValueError as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process OAuth callback"
        )


@router.get("/", response_model=EbayAccountListResponse)
def list_ebay_accounts(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get list of connected eBay accounts

    **Returns:**
    - List of eBay accounts for current tenant
    """
    accounts = db.query(EbayAccount).filter(
        EbayAccount.tenant_id == current_tenant.id
    ).all()

    return EbayAccountListResponse(
        accounts=[EbayAccountResponse(**account.to_dict()) for account in accounts],
        total=len(accounts)
    )


@router.get("/status", response_model=OAuthStatus)
def get_oauth_status(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get OAuth connection status

    **Returns:**
    - is_connected: Whether OAuth is set up
    - has_valid_token: Whether token is valid and not expired
    - access_token_expires_at: Token expiration time
    - accounts_count: Number of connected accounts
    - accounts: List of connected accounts
    """
    credential = db.query(OAuthCredential).filter(
        OAuthCredential.tenant_id == current_tenant.id,
        OAuthCredential.is_valid == True
    ).first()

    accounts = db.query(EbayAccount).filter(
        EbayAccount.tenant_id == current_tenant.id
    ).all()

    if not credential:
        return OAuthStatus(
            is_connected=False,
            has_valid_token=False,
            access_token_expires_at=None,
            accounts_count=0,
            accounts=[]
        )

    return OAuthStatus(
        is_connected=True,
        has_valid_token=not credential.is_access_token_expired(),
        access_token_expires_at=credential.access_token_expires_at,
        accounts_count=len(accounts),
        accounts=[EbayAccountResponse(**account.to_dict()) for account in accounts]
    )


@router.delete("/{account_id}", status_code=status.HTTP_200_OK)
def delete_ebay_account(
    account_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Delete an eBay account connection

    **Path Parameters:**
    - account_id: eBay account ID to delete

    **Returns:**
    - Success message
    """
    account = db.query(EbayAccount).filter(
        EbayAccount.id == account_id,
        EbayAccount.tenant_id == current_tenant.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="eBay account not found"
        )

    db.delete(account)
    db.commit()

    logger.info(f"Deleted eBay account {account_id} for tenant {current_tenant.id}")

    return {"message": "eBay account deleted successfully"}


@router.delete("/oauth/disconnect", status_code=status.HTTP_200_OK)
def disconnect_oauth(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Disconnect OAuth (delete all credentials and accounts)

    **Returns:**
    - Success message
    """
    oauth_service = EbayOAuthService()
    deleted = oauth_service.delete_oauth_credentials(db, current_tenant)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OAuth credentials found"
        )

    logger.info(f"Disconnected OAuth for tenant: {current_tenant.id}")

    return {"message": "eBay OAuth disconnected successfully"}
