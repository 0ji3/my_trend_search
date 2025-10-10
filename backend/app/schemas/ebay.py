"""
eBay OAuth and Account Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# OAuth Schemas

class OAuthAuthorizationURL(BaseModel):
    """OAuth authorization URL response"""
    authorization_url: str = Field(..., description="eBay OAuth authorization URL")
    state: str = Field(..., description="State parameter for CSRF protection")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request"""
    code: str = Field(..., description="Authorization code from eBay")
    state: Optional[str] = Field(None, description="State parameter for validation")


class OAuthTokenResponse(BaseModel):
    """OAuth token information (without sensitive data)"""
    id: str
    tenant_id: str
    access_token_expires_at: datetime
    refresh_token_expires_at: Optional[datetime]
    scopes: List[str]
    is_valid: bool
    created_at: datetime
    updated_at: datetime


# eBay Account Schemas

class EbayAccountBase(BaseModel):
    """Base eBay account schema"""
    ebay_user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    marketplace_id: str = "EBAY_US"


class EbayAccountCreate(EbayAccountBase):
    """Schema for creating eBay account"""
    oauth_credential_id: str
    tenant_id: str


class EbayAccountResponse(BaseModel):
    """eBay account response schema"""
    id: str
    tenant_id: str
    oauth_credential_id: str
    ebay_user_id: str
    username: Optional[str]
    email: Optional[str]
    marketplace_id: str
    is_active: bool
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EbayAccountListResponse(BaseModel):
    """List of eBay accounts"""
    accounts: List[EbayAccountResponse]
    total: int


# OAuth Status Schema

class OAuthStatus(BaseModel):
    """OAuth connection status"""
    is_connected: bool
    has_valid_token: bool
    access_token_expires_at: Optional[datetime]
    accounts_count: int
    accounts: List[EbayAccountResponse]
