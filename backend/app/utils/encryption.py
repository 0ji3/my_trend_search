"""
Token Encryption Utilities - AES-256-GCM
"""
import os
import base64
from typing import Dict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get encryption key from settings

    The key should be a base64-encoded 32-byte key.
    Generate with: base64.b64encode(os.urandom(32)).decode()
    """
    try:
        key_str = settings.ENCRYPTION_KEY
        if not key_str:
            raise ValueError("ENCRYPTION_KEY not set in environment")

        # Decode base64 key
        key = base64.b64decode(key_str)

        if len(key) != 32:
            raise ValueError(f"Encryption key must be 32 bytes, got {len(key)} bytes")

        return key
    except Exception as e:
        logger.error(f"Failed to get encryption key: {e}")
        raise


def encrypt_token(plaintext: str) -> Dict[str, bytes]:
    """
    Encrypt a token using AES-256-GCM

    Args:
        plaintext: Token to encrypt

    Returns:
        dict: {
            'ciphertext': encrypted data (without auth tag),
            'iv': initialization vector (12 bytes),
            'auth_tag': authentication tag (16 bytes)
        }

    Raises:
        ValueError: If encryption fails
    """
    try:
        # Get encryption key
        key = get_encryption_key()

        # Create AES-GCM cipher
        aesgcm = AESGCM(key)

        # Generate random IV (12 bytes for GCM)
        iv = os.urandom(12)

        # Encrypt (returns ciphertext + auth tag)
        ciphertext_and_tag = aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)

        # Split ciphertext and auth tag
        # GCM auth tag is always 16 bytes at the end
        ciphertext = ciphertext_and_tag[:-16]
        auth_tag = ciphertext_and_tag[-16:]

        return {
            'ciphertext': ciphertext,
            'iv': iv,
            'auth_tag': auth_tag
        }
    except Exception as e:
        logger.error(f"Token encryption failed: {e}")
        raise ValueError(f"Failed to encrypt token: {e}")


def decrypt_token(ciphertext: bytes, iv: bytes, auth_tag: bytes) -> str:
    """
    Decrypt a token using AES-256-GCM

    Args:
        ciphertext: Encrypted data
        iv: Initialization vector (12 bytes)
        auth_tag: Authentication tag (16 bytes)

    Returns:
        str: Decrypted plaintext token

    Raises:
        ValueError: If decryption fails (invalid key, corrupted data, etc.)
    """
    try:
        # Get encryption key
        key = get_encryption_key()

        # Create AES-GCM cipher
        aesgcm = AESGCM(key)

        # Reconstruct ciphertext + tag
        ciphertext_and_tag = ciphertext + auth_tag

        # Decrypt
        plaintext_bytes = aesgcm.decrypt(iv, ciphertext_and_tag, None)

        return plaintext_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Token decryption failed: {e}")
        raise ValueError(f"Failed to decrypt token: {e}")


def encrypt_oauth_tokens(access_token: str, refresh_token: str) -> Dict[str, bytes]:
    """
    Encrypt both access and refresh tokens

    Args:
        access_token: OAuth access token
        refresh_token: OAuth refresh token

    Returns:
        dict: {
            'access_token_encrypted': bytes,
            'access_token_iv': bytes,
            'access_token_auth_tag': bytes,
            'refresh_token_encrypted': bytes,
            'refresh_token_iv': bytes,
            'refresh_token_auth_tag': bytes,
        }
    """
    access_result = encrypt_token(access_token)
    refresh_result = encrypt_token(refresh_token)

    return {
        'access_token_encrypted': access_result['ciphertext'],
        'access_token_iv': access_result['iv'],
        'access_token_auth_tag': access_result['auth_tag'],
        'refresh_token_encrypted': refresh_result['ciphertext'],
        'refresh_token_iv': refresh_result['iv'],
        'refresh_token_auth_tag': refresh_result['auth_tag'],
    }


def decrypt_oauth_tokens(
    access_token_encrypted: bytes,
    access_token_iv: bytes,
    access_token_auth_tag: bytes,
    refresh_token_encrypted: bytes,
    refresh_token_iv: bytes,
    refresh_token_auth_tag: bytes
) -> Dict[str, str]:
    """
    Decrypt both access and refresh tokens

    Returns:
        dict: {
            'access_token': str,
            'refresh_token': str
        }
    """
    access_token = decrypt_token(
        access_token_encrypted,
        access_token_iv,
        access_token_auth_tag
    )

    refresh_token = decrypt_token(
        refresh_token_encrypted,
        refresh_token_iv,
        refresh_token_auth_tag
    )

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }
