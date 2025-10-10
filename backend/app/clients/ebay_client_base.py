"""
eBay API Base Client
Provides common functionality for all eBay API clients
"""
import os
import requests
from typing import Dict, Any, Optional
from app.config import settings


class EbayClientBase:
    """
    Base class for eBay API clients
    Provides common configuration and utilities
    """

    # Mock mode flag (can be overridden by environment variable)
    MOCK_MODE = os.getenv('EBAY_MOCK_MODE', 'true').lower() == 'true'

    def __init__(self):
        self.environment = getattr(settings, 'EBAY_ENVIRONMENT', 'sandbox')
        self.client_id = getattr(settings, 'EBAY_CLIENT_ID', 'mock_client_id')
        self.client_secret = getattr(settings, 'EBAY_CLIENT_SECRET', 'mock_client_secret')

    def _should_use_mock(self) -> bool:
        """
        Determine if mock mode should be used
        Mock mode is enabled when:
        1. EBAY_MOCK_MODE env var is 'true', OR
        2. EBAY_CLIENT_ID is not configured or is 'mock_client_id'
        """
        if self.MOCK_MODE:
            return True
        if self.client_id in [None, '', 'mock_client_id']:
            return True
        return False

    def _get_base_url(self, api_type: str) -> str:
        """
        Get base URL for specific API type

        Args:
            api_type: 'trading', 'inventory', 'analytics', 'feed', 'auth'
        """
        if self.environment == 'production':
            urls = {
                'trading': 'https://api.ebay.com/ws/api.dll',
                'inventory': 'https://api.ebay.com/sell/inventory/v1',
                'analytics': 'https://api.ebay.com/sell/analytics/v1',
                'feed': 'https://api.ebay.com/sell/feed/v1',
                'auth': 'https://api.ebay.com/identity/v1/oauth2',
            }
        else:  # sandbox
            urls = {
                'trading': 'https://api.sandbox.ebay.com/ws/api.dll',
                'inventory': 'https://api.sandbox.ebay.com/sell/inventory/v1',
                'analytics': 'https://api.sandbox.ebay.com/sell/analytics/v1',
                'feed': 'https://api.sandbox.ebay.com/sell/feed/v1',
                'auth': 'https://api.sandbox.ebay.com/identity/v1/oauth2',
            }

        return urls.get(api_type, '')

    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make HTTP request with error handling

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            headers: Request headers
            data: Request body (for XML/text)
            json: Request body (for JSON)
            params: Query parameters

        Returns:
            requests.Response object

        Raises:
            requests.HTTPError: If request fails
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            # Log error details
            print(f"eBay API Error: {e}")
            print(f"Response: {e.response.text if e.response else 'No response'}")
            raise
        except requests.RequestException as e:
            print(f"Request Error: {e}")
            raise


class EbayAPIError(Exception):
    """Base exception for eBay API errors"""
    pass


class EbayAuthError(EbayAPIError):
    """OAuth token invalid or expired"""
    pass


class EbayRateLimitError(EbayAPIError):
    """API rate limit exceeded"""
    pass


class EbayItemNotFoundError(EbayAPIError):
    """Item no longer exists"""
    pass


def handle_ebay_api_error(response: requests.Response):
    """
    Parse eBay error response and raise appropriate exception

    Args:
        response: requests.Response object

    Raises:
        EbayAuthError: If authentication failed
        EbayRateLimitError: If rate limit exceeded
        EbayItemNotFoundError: If item not found
        requests.HTTPError: For other HTTP errors
    """
    if response.status_code == 401:
        raise EbayAuthError("Access token expired or invalid")
    elif response.status_code == 429:
        raise EbayRateLimitError("API rate limit exceeded")
    elif response.status_code == 404:
        raise EbayItemNotFoundError("Item not found")
    else:
        response.raise_for_status()
