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
        import base64
        import json

        oauth_service = EbayOAuthService()

        # Generate base state
        auth_url, base_state = oauth_service.generate_authorization_url()

        # Encode tenant_id in state parameter
        state_data = {
            'tenant_id': str(current_tenant.id),
            'random': base_state
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        # Replace state in auth_url
        auth_url = auth_url.replace(f"state={base_state}", f"state={state}")

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


@router.get("/callback", status_code=status.HTTP_302_FOUND)
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from eBay

    This endpoint is called by eBay after user authorization.
    No authentication required as eBay redirects here.
    The state parameter is used to identify the tenant.

    **Query Parameters:**
    - code: Authorization code from eBay
    - state: State parameter containing tenant_id

    **Returns:**
    - Redirect to frontend with success/error status
    """
    from fastapi.responses import RedirectResponse
    import base64
    import json

    try:
        oauth_service = EbayOAuthService()

        # Decode tenant_id from state parameter
        tenant_id = None
        if state:
            try:
                state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
                tenant_id = state_data.get('tenant_id')
            except Exception as e:
                logger.warning(f"Failed to decode state parameter: {e}")

        # If no state or failed to decode, use the first tenant (for backward compatibility)
        if not tenant_id:
            from app.models.tenant import Tenant
            tenant = db.query(Tenant).order_by(Tenant.created_at.desc()).first()
            if not tenant:
                logger.error("No tenant found in database")
                return RedirectResponse(url="http://localhost:3000/dashboard?ebay_error=no_tenant_found")
            tenant_id = tenant.id
            logger.warning(f"No state parameter provided, using most recent tenant: {tenant_id}")
        else:
            # Get tenant by ID from state
            from app.models.tenant import Tenant
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                logger.error(f"Tenant not found: {tenant_id}")
                return RedirectResponse(url="http://localhost:3000/dashboard?ebay_error=tenant_not_found")

        # Exchange code for tokens
        tokens = oauth_service.exchange_code_for_tokens(code)

        # Save credentials
        credential = oauth_service.save_oauth_credentials(
            db=db,
            tenant=tenant,
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            expires_in=tokens['expires_in'],
            refresh_token_expires_in=tokens['refresh_token_expires_in']
        )

        logger.info(f"OAuth callback successful for tenant: {tenant.id}")

        # Fetch and update eBay user information
        try:
            from app.services.ebay_user_service import EbayUserService
            user_service = EbayUserService()
            account = await user_service.fetch_and_update_user_info(db, credential)

            if account:
                logger.info(
                    f"Successfully fetched eBay user info: "
                    f"userId={account.ebay_user_id}, username={account.username}"
                )
            else:
                logger.warning("Failed to fetch eBay user info, but OAuth connection is successful")
        except Exception as e:
            logger.error(f"Error fetching eBay user info: {e}")
            # Don't fail the whole OAuth process if user info fetch fails
            # The OAuth connection is still valid

        # Redirect to frontend success page
        return RedirectResponse(url="http://localhost:3000/dashboard?ebay_connected=true")

    except ValueError as e:
        logger.error(f"OAuth callback failed: {e}")
        return RedirectResponse(url="http://localhost:3000/dashboard?ebay_error=auth_failed")
    except Exception as e:
        logger.error(f"Unexpected error during OAuth callback: {e}")
        return RedirectResponse(url="http://localhost:3000/dashboard?ebay_error=unknown")


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
    # Get all accounts for this tenant
    accounts = db.query(EbayAccount).filter(
        EbayAccount.tenant_id == current_tenant.id
    ).all()

    if not accounts:
        return OAuthStatus(
            is_connected=False,
            has_valid_token=False,
            access_token_expires_at=None,
            accounts_count=0,
            accounts=[]
        )

    # Get the most recent valid credential (for display purposes)
    credential = db.query(OAuthCredential).filter(
        OAuthCredential.tenant_id == current_tenant.id,
        OAuthCredential.is_valid == True
    ).order_by(OAuthCredential.created_at.desc()).first()

    if not credential:
        # Have accounts but no valid credentials (shouldn't happen)
        return OAuthStatus(
            is_connected=True,
            has_valid_token=False,
            access_token_expires_at=None,
            accounts_count=len(accounts),
            accounts=[EbayAccountResponse(**account.to_dict()) for account in accounts]
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


@router.post("/sync-user-info", status_code=status.HTTP_200_OK)
async def sync_user_info(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Manually sync eBay user information for all existing OAuth connections

    **Returns:**
    - Updated eBay account information for all accounts
    """
    # Get all OAuth credentials
    credentials = db.query(OAuthCredential).filter(
        OAuthCredential.tenant_id == current_tenant.id,
        OAuthCredential.is_valid == True
    ).all()

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid OAuth credentials found. Please connect your eBay account first."
        )

    # Fetch and update user info for all credentials
    from app.services.ebay_user_service import EbayUserService
    user_service = EbayUserService()

    accounts = []
    for credential in credentials:
        account = await user_service.fetch_and_update_user_info(db, credential)
        if account:
            accounts.append(account)

    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch eBay user information for all accounts"
        )

    logger.info(f"Manually synced user info for {len(accounts)} account(s), tenant: {current_tenant.id}")

    return {
        "message": f"eBay user information synced successfully for {len(accounts)} account(s)",
        "accounts": [EbayAccountResponse(**account.to_dict()) for account in accounts]
    }


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
