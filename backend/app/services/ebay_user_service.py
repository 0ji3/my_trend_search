"""
eBay User Service

Handles eBay Commerce Identity API for fetching user information
"""
import logging
import requests
from typing import Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
from app.models.oauth_credential import OAuthCredential
from app.models.ebay_account import EbayAccount

logger = logging.getLogger(__name__)


class EbayUserService:
    """eBay User API service for fetching user information"""

    def __init__(self):
        self.environment = settings.EBAY_ENVIRONMENT
        # Use correct API base URL for Identity API
        if self.environment == "sandbox":
            self.api_base_url = "https://apiz.sandbox.ebay.com"
        else:
            self.api_base_url = "https://apiz.ebay.com"

    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """
        Fetch user information using access token

        API: GET /commerce/identity/v1/user/
        Docs: https://developer.ebay.com/api-docs/commerce/identity/resources/user/methods/getUser

        Args:
            access_token: OAuth access token

        Returns:
            dict: User information including userId, username, email, etc.
            None: If API call fails

        Response example:
        {
            "userId": "testuser123",
            "username": "test_seller",
            "email": "seller@example.com",
            "registrationMarketplaceId": "EBAY_US",
            "status": "CONFIRMED",
            "userFirstName": "Test",
            "userLastName": "Seller"
        }
        """
        url = f"{self.api_base_url}/commerce/identity/v1/user/"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            logger.info(f"Fetching user info from eBay Identity API: {url}")
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Successfully fetched user info for userId: {user_data.get('userId')}")
                return user_data
            else:
                logger.error(
                    f"Failed to fetch user info. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling eBay User API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user_info: {e}")
            return None

    def update_ebay_account_info(
        self,
        db: Session,
        credential: OAuthCredential,
        user_info: Dict
    ) -> Optional[EbayAccount]:
        """
        Update ebay_accounts table with real user information

        Before: モックデータ (test_ebay_user_123, test_seller)
        After: 実データ (actual_user_id, actual_username)

        Args:
            db: Database session
            credential: OAuth credential
            user_info: User information from Identity API

        Returns:
            EbayAccount: Updated account object
            None: If update fails
        """
        try:
            ebay_user_id = user_info.get('userId', 'unknown')

            # First, check if this eBay user is already connected to this tenant
            existing_account = db.query(EbayAccount).filter(
                EbayAccount.tenant_id == credential.tenant_id,
                EbayAccount.ebay_user_id == ebay_user_id
            ).first()

            if existing_account:
                # eBay account already exists for this tenant
                # Update the account with new credential and user info
                existing_account.oauth_credential_id = credential.id
                existing_account.username = user_info.get('username', existing_account.username)
                existing_account.email = user_info.get('email', existing_account.email)
                existing_account.marketplace_id = user_info.get('registrationMarketplaceId', existing_account.marketplace_id)
                existing_account.is_active = True
                existing_account.updated_at = datetime.utcnow()

                logger.info(
                    f"Updated existing eBay account (already connected): "
                    f"userId={existing_account.ebay_user_id}, username={existing_account.username}"
                )

                db.commit()
                db.refresh(existing_account)
                return existing_account
            else:
                # Check if there's an account linked to this credential
                # (from previous OAuth flow, before user info was fetched)
                account = db.query(EbayAccount).filter(
                    EbayAccount.oauth_credential_id == credential.id
                ).first()

                if account:
                    # Update existing account
                    account.ebay_user_id = ebay_user_id
                    account.username = user_info.get('username', account.username)
                    account.email = user_info.get('email', account.email)
                    account.marketplace_id = user_info.get('registrationMarketplaceId', account.marketplace_id)

                    logger.info(f"Updated existing eBay account: {account.ebay_user_id}")
                else:
                    # Create new account
                    account = EbayAccount(
                        oauth_credential_id=credential.id,
                        tenant_id=credential.tenant_id,
                        ebay_user_id=ebay_user_id,
                        username=user_info.get('username'),
                        email=user_info.get('email'),
                        marketplace_id=user_info.get('registrationMarketplaceId', 'EBAY_US'),
                        is_active=True
                    )
                    db.add(account)
                    logger.info(f"Created new eBay account: {account.ebay_user_id}")

                db.commit()
                db.refresh(account)
                return account

        except Exception as e:
            logger.error(f"Error updating eBay account info: {e}")
            db.rollback()
            return None

    async def fetch_and_update_user_info(
        self,
        db: Session,
        credential: OAuthCredential
    ) -> Optional[EbayAccount]:
        """
        Convenience method to fetch user info and update account in one call

        Args:
            db: Database session
            credential: OAuth credential with access token

        Returns:
            EbayAccount: Updated account object
            None: If process fails
        """
        # Get valid access token using EbayOAuthService
        from app.services.ebay_oauth_service import EbayOAuthService
        oauth_service = EbayOAuthService()

        try:
            access_token = await oauth_service.get_valid_access_token(db, credential.tenant_id)
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

        if not access_token:
            logger.error("Failed to get access token")
            return None

        # Fetch user info from eBay
        user_info = self.get_user_info(access_token)

        if not user_info:
            logger.error("Failed to fetch user info from eBay")
            return None

        # Update account with real data
        account = self.update_ebay_account_info(db, credential, user_info)

        if account:
            logger.info(
                f"Successfully fetched and updated user info for "
                f"userId: {account.ebay_user_id}, username: {account.username}"
            )

        return account
