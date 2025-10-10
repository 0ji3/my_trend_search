"""
Authentication Service
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Tuple
from datetime import timedelta
import logging

from app.models.tenant import Tenant, TenantStatus
from app.schemas.auth import (
    TenantCreate,
    TokenResponse,
    LoginRequest,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user management"""

    @staticmethod
    def register_tenant(db: Session, tenant_data: TenantCreate) -> Tenant:
        """
        Register a new tenant (user)

        Args:
            db: Database session
            tenant_data: Tenant registration data

        Returns:
            Tenant: Created tenant object

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing_tenant = db.query(Tenant).filter(
            Tenant.email == tenant_data.email
        ).first()

        if existing_tenant:
            logger.warning(f"Registration attempt with existing email: {tenant_data.email}")
            raise ValueError("Email already registered")

        # Hash password
        hashed_password = hash_password(tenant_data.password)

        # Create tenant
        new_tenant = Tenant(
            email=tenant_data.email,
            password_hash=hashed_password,
            business_name=tenant_data.business_name,
            timezone=tenant_data.timezone,
            status="active",  # Use string value directly
        )

        try:
            db.add(new_tenant)
            db.commit()
            db.refresh(new_tenant)
            logger.info(f"New tenant registered: {new_tenant.id}")
            return new_tenant

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during registration: {e}")
            raise ValueError("Email already registered")

    @staticmethod
    def authenticate_tenant(db: Session, login_data: LoginRequest) -> Optional[Tenant]:
        """
        Authenticate a tenant with email and password

        Args:
            db: Database session
            login_data: Login credentials

        Returns:
            Optional[Tenant]: Authenticated tenant or None
        """
        tenant = db.query(Tenant).filter(
            Tenant.email == login_data.email
        ).first()

        if not tenant:
            logger.warning(f"Login attempt with non-existent email: {login_data.email}")
            return None

        if tenant.status != "active":
            logger.warning(f"Login attempt for inactive account: {tenant.id}")
            return None

        if not verify_password(login_data.password, tenant.password_hash):
            logger.warning(f"Failed login attempt for tenant: {tenant.id}")
            return None

        logger.info(f"Successful login for tenant: {tenant.id}")
        return tenant

    @staticmethod
    def create_tokens(tenant: Tenant) -> TokenResponse:
        """
        Create access and refresh tokens for a tenant

        Args:
            tenant: Authenticated tenant

        Returns:
            TokenResponse: Access and refresh tokens
        """
        token_data = {
            "sub": str(tenant.id),
            "email": tenant.email,
        }

        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        )

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Optional[TokenResponse]:
        """
        Refresh access token using refresh token

        Args:
            db: Database session
            refresh_token: Refresh token

        Returns:
            Optional[TokenResponse]: New tokens or None if invalid
        """
        token_data = verify_token(refresh_token, token_type="refresh")

        if not token_data:
            logger.warning("Invalid or expired refresh token")
            return None

        # Verify tenant still exists and is active
        tenant = db.query(Tenant).filter(
            Tenant.id == token_data.tenant_id
        ).first()

        if not tenant or tenant.status != "active":
            logger.warning(f"Refresh token used for non-existent or inactive tenant: {token_data.tenant_id}")
            return None

        # Create new tokens
        return AuthService.create_tokens(tenant)

    @staticmethod
    def get_current_tenant(db: Session, access_token: str) -> Optional[Tenant]:
        """
        Get current tenant from access token

        Args:
            db: Database session
            access_token: Access token

        Returns:
            Optional[Tenant]: Current tenant or None if invalid
        """
        token_data = verify_token(access_token, token_type="access")

        if not token_data:
            return None

        tenant = db.query(Tenant).filter(
            Tenant.id == token_data.tenant_id
        ).first()

        if not tenant or tenant.status != "active":
            return None

        return tenant

    @staticmethod
    def change_password(
        db: Session,
        tenant: Tenant,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change tenant password

        Args:
            db: Database session
            tenant: Current tenant
            current_password: Current password
            new_password: New password

        Returns:
            bool: True if successful
        """
        # Verify current password
        if not verify_password(current_password, tenant.password_hash):
            logger.warning(f"Password change failed - incorrect current password for tenant: {tenant.id}")
            return False

        # Update password
        tenant.password_hash = hash_password(new_password)
        db.commit()
        logger.info(f"Password changed for tenant: {tenant.id}")
        return True
