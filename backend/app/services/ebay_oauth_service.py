"""
eBay OAuth Service
"""
import base64
import secrets
import requests
from sqlalchemy.orm import Session
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

from app.config import settings
from app.models.tenant import Tenant
from app.models.oauth_credential import OAuthCredential
from app.models.ebay_account import EbayAccount
from app.utils.encryption import encrypt_oauth_tokens, decrypt_oauth_tokens

logger = logging.getLogger(__name__)


class EbayOAuthService:
    """eBay OAuth 2.0 service"""

    # eBay OAuth endpoints
    SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com/oauth2/authorize"
    PRODUCTION_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
    SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    PRODUCTION_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

    # Required scopes
    REQUIRED_SCOPES = [
        "https://api.ebay.com/oauth/api_scope/sell.inventory",
        "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
        "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
        "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly",  # For Commerce Identity API
    ]

    def __init__(self):
        self.client_id = settings.EBAY_CLIENT_ID
        self.client_secret = settings.EBAY_CLIENT_SECRET
        self.redirect_uri = settings.EBAY_REDIRECT_URI
        self.environment = settings.EBAY_ENVIRONMENT

        # Select URLs based on environment
        if self.environment == "production":
            self.auth_url = self.PRODUCTION_AUTH_URL
            self.token_url = self.PRODUCTION_TOKEN_URL
        else:
            self.auth_url = self.SANDBOX_AUTH_URL
            self.token_url = self.SANDBOX_TOKEN_URL

    def _get_basic_auth_header(self) -> str:
        """Generate Basic Auth header for token requests"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def generate_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate eBay OAuth authorization URL

        Args:
            state: Optional state parameter (will be generated if not provided)

        Returns:
            tuple: (authorization_url, state)
        """
        if not state:
            state = secrets.token_urlsafe(32)

        scopes = " ".join(self.REQUIRED_SCOPES)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "state": state,
        }

        # Build URL
        param_str = "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())
        authorization_url = f"{self.auth_url}?{param_str}"

        logger.info(f"Generated eBay authorization URL with state: {state}")
        logger.info(f"OAuth Parameters: client_id={self.client_id[:50]}..., redirect_uri={self.redirect_uri}, scopes={len(self.REQUIRED_SCOPES)} scopes")
        logger.info(f"Full Authorization URL: {authorization_url[:200]}...")

        return authorization_url, state

    def exchange_code_for_tokens(self, authorization_code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            authorization_code: Authorization code from eBay callback

        Returns:
            dict: {
                'access_token': str,
                'refresh_token': str,
                'expires_in': int,  # seconds
                'refresh_token_expires_in': int,  # seconds
            }

        Raises:
            ValueError: If token exchange fails
        """
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": self._get_basic_auth_header(),
            }

            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri,
            }

            response = requests.post(
                self.token_url,
                headers=headers,
                data=data,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"eBay token exchange failed: {response.status_code} - {response.text}")
                raise ValueError(f"Token exchange failed: {response.text}")

            token_data = response.json()

            logger.info("Successfully exchanged authorization code for tokens")

            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'expires_in': token_data['expires_in'],
                'refresh_token_expires_in': token_data.get('refresh_token_expires_in', 47304000),  # ~18 months default
            }

        except requests.RequestException as e:
            logger.error(f"Network error during token exchange: {e}")
            raise ValueError(f"Failed to connect to eBay: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            raise ValueError(f"Token exchange failed: {e}")

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: eBay refresh token

        Returns:
            dict: {
                'access_token': str,
                'expires_in': int,
            }

        Raises:
            ValueError: If token refresh fails
        """
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": self._get_basic_auth_header(),
            }

            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": " ".join(self.REQUIRED_SCOPES),
            }

            response = requests.post(
                self.token_url,
                headers=headers,
                data=data,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"eBay token refresh failed: {response.status_code} - {response.text}")
                raise ValueError(f"Token refresh failed: {response.text}")

            token_data = response.json()

            logger.info("Successfully refreshed access token")

            return {
                'access_token': token_data['access_token'],
                'expires_in': token_data['expires_in'],
            }

        except requests.RequestException as e:
            logger.error(f"Network error during token refresh: {e}")
            raise ValueError(f"Failed to connect to eBay: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise ValueError(f"Token refresh failed: {e}")

    def save_oauth_credentials(
        self,
        db: Session,
        tenant: Tenant,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        refresh_token_expires_in: int
    ) -> OAuthCredential:
        """
        Save OAuth credentials to database (encrypted)

        For multi-account support, always creates a new credential.
        Each eBay account has its own access token, so each needs a separate credential.

        Args:
            db: Database session
            tenant: Tenant object
            access_token: Access token
            refresh_token: Refresh token
            expires_in: Access token expiration (seconds)
            refresh_token_expires_in: Refresh token expiration (seconds)

        Returns:
            OAuthCredential: Created credential
        """
        # Encrypt tokens
        encrypted_data = encrypt_oauth_tokens(access_token, refresh_token)

        # Calculate expiration times
        access_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        refresh_token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_token_expires_in)

        # Always create new credential for multi-account support
        credential = OAuthCredential(
            tenant_id=tenant.id,
            access_token_encrypted=encrypted_data['access_token_encrypted'],
            access_token_iv=encrypted_data['access_token_iv'],
            access_token_auth_tag=encrypted_data['access_token_auth_tag'],
            refresh_token_encrypted=encrypted_data['refresh_token_encrypted'],
            refresh_token_iv=encrypted_data['refresh_token_iv'],
            refresh_token_auth_tag=encrypted_data['refresh_token_auth_tag'],
            access_token_expires_at=access_token_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
            scopes=self.REQUIRED_SCOPES,
            is_valid=True,
        )
        db.add(credential)

        logger.info(f"Created new OAuth credential for tenant: {tenant.id}")

        db.commit()
        db.refresh(credential)

        return credential

    async def get_valid_access_token(self, db: Session, tenant_id) -> Optional[str]:
        """
        Get valid access token for tenant (auto-refresh if expired)

        Args:
            db: Database session
            tenant_id: Tenant ID (UUID or Tenant object)

        Returns:
            str: Valid access token or None if not available

        Raises:
            ValueError: If token refresh fails
        """
        # Handle both UUID and Tenant object
        if hasattr(tenant_id, 'id'):
            tenant_id = tenant_id.id

        credential = db.query(OAuthCredential).filter(
            OAuthCredential.tenant_id == tenant_id,
            OAuthCredential.is_valid == True
        ).first()

        if not credential:
            return None

        # Check if access token is expired
        if not credential.is_access_token_expired():
            # Token still valid, decrypt and return
            tokens = decrypt_oauth_tokens(
                credential.access_token_encrypted,
                credential.access_token_iv,
                credential.access_token_auth_tag,
                credential.refresh_token_encrypted,
                credential.refresh_token_iv,
                credential.refresh_token_auth_tag
            )
            return tokens['access_token']

        # Access token expired, try to refresh
        logger.info(f"Access token expired for tenant {tenant_id}, refreshing...")

        # Decrypt refresh token
        tokens = decrypt_oauth_tokens(
            credential.access_token_encrypted,
            credential.access_token_iv,
            credential.access_token_auth_tag,
            credential.refresh_token_encrypted,
            credential.refresh_token_iv,
            credential.refresh_token_auth_tag
        )

        # Refresh access token
        new_tokens = self.refresh_access_token(tokens['refresh_token'])

        # Update credential
        encrypted_data = encrypt_oauth_tokens(
            new_tokens['access_token'],
            tokens['refresh_token']  # Refresh token doesn't change
        )

        credential.access_token_encrypted = encrypted_data['access_token_encrypted']
        credential.access_token_iv = encrypted_data['access_token_iv']
        credential.access_token_auth_tag = encrypted_data['access_token_auth_tag']
        credential.access_token_expires_at = datetime.utcnow() + timedelta(seconds=new_tokens['expires_in'])
        credential.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Successfully refreshed access token for tenant: {tenant_id}")

        return new_tokens['access_token']

    def delete_oauth_credentials(self, db: Session, tenant: Tenant) -> bool:
        """
        Delete all OAuth credentials for tenant

        Args:
            db: Database session
            tenant: Tenant object

        Returns:
            bool: True if deleted, False if not found
        """
        credentials = db.query(OAuthCredential).filter(
            OAuthCredential.tenant_id == tenant.id
        ).all()

        if not credentials:
            return False

        for credential in credentials:
            db.delete(credential)

        db.commit()

        logger.info(f"Deleted {len(credentials)} OAuth credential(s) for tenant: {tenant.id}")

        return True
