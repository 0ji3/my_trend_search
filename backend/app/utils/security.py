"""
Security Utilities - Password Hashing and JWT
"""
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from app.config import settings
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False  # Allow passwords longer than 72 bytes (will auto-truncate)
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    # Bcrypt has a maximum password length of 72 bytes
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload data to encode
        expires_delta: Token expiration time (optional)

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token

    Args:
        data: Payload data to encode
        expires_delta: Token expiration time (optional)

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData: Decoded token data or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(f"Invalid token type. Expected {token_type}, got {payload.get('type')}")
            return None

        tenant_id: str = payload.get("sub")
        email: str = payload.get("email")
        exp: int = payload.get("exp")

        if tenant_id is None or email is None:
            logger.warning("Token missing required fields")
            return None

        return TokenData(tenant_id=tenant_id, email=email, exp=exp)

    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification (for debugging)

    Args:
        token: JWT token to decode

    Returns:
        Dict: Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        return None
