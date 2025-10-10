"""
Authentication API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db
from app.schemas.auth import (
    TenantCreate,
    TenantResponse,
    LoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    PasswordChangeRequest,
)
from app.services.auth_service import AuthService
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Dependency to get current authenticated tenant

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        Tenant: Current authenticated tenant

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    tenant = AuthService.get_current_tenant(db, token)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return tenant


@router.post("/register", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def register(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user

    **Request Body:**
    - email: Valid email address
    - password: Strong password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)
    - business_name: Optional business name
    - timezone: Timezone (default: UTC)

    **Returns:**
    - Tenant information (without password)
    """
    try:
        tenant = AuthService.register_tenant(db, tenant_data)
        logger.info(f"Tenant registered successfully: {tenant.id}")
        return TenantResponse(**tenant.to_dict())

    except ValueError as e:
        logger.warning(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later."
        )


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password

    **Request Body:**
    - email: User email
    - password: User password

    **Returns:**
    - access_token: JWT access token (expires in 24 hours)
    - refresh_token: JWT refresh token (expires in 30 days)
    - token_type: "bearer"
    - expires_in: Token expiration time in seconds
    """
    tenant = AuthService.authenticate_tenant(db, login_data)

    if not tenant:
        logger.warning(f"Login failed for email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = AuthService.create_tokens(tenant)
    logger.info(f"Login successful for tenant: {tenant.id}")
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token

    **Request Body:**
    - refresh_token: Valid refresh token

    **Returns:**
    - New access and refresh tokens
    """
    tokens = AuthService.refresh_access_token(db, refresh_data.refresh_token)

    if not tokens:
        logger.warning("Token refresh failed - invalid or expired refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Token refreshed successfully")
    return tokens


@router.get("/me", response_model=TenantResponse)
def get_current_user(
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """
    Get current user information

    **Headers:**
    - Authorization: Bearer {access_token}

    **Returns:**
    - Current user information
    """
    return TenantResponse(**current_tenant.to_dict())


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    password_data: PasswordChangeRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Change current user's password

    **Headers:**
    - Authorization: Bearer {access_token}

    **Request Body:**
    - current_password: Current password
    - new_password: New password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit)

    **Returns:**
    - Success message
    """
    success = AuthService.change_password(
        db,
        current_tenant,
        password_data.current_password,
        password_data.new_password
    )

    if not success:
        logger.warning(f"Password change failed for tenant: {current_tenant.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    logger.info(f"Password changed successfully for tenant: {current_tenant.id}")
    return {"message": "Password changed successfully"}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """
    Logout current user

    **Headers:**
    - Authorization: Bearer {access_token}

    **Returns:**
    - Success message

    **Note:** This is a stateless JWT implementation.
    The client should discard the tokens on logout.
    """
    logger.info(f"Logout for tenant: {current_tenant.id}")
    return {"message": "Logged out successfully"}
