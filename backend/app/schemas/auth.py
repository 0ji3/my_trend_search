"""
Authentication Schemas (Pydantic)
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class TenantBase(BaseModel):
    """Base tenant schema"""
    email: EmailStr
    business_name: Optional[str] = None
    timezone: str = "UTC"


class TenantCreate(TenantBase):
    """Schema for creating a new tenant (registration)"""
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class TenantUpdate(BaseModel):
    """Schema for updating tenant information"""
    business_name: Optional[str] = None
    timezone: Optional[str] = None


class TenantResponse(TenantBase):
    """Schema for tenant response (public info)"""
    id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class TokenData(BaseModel):
    """Schema for token payload data"""
    tenant_id: str
    email: str
    exp: Optional[int] = None
