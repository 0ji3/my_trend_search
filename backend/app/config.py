"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "eBay Trend Research Tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # eBay API
    EBAY_CLIENT_ID: str
    EBAY_CLIENT_SECRET: str
    EBAY_REDIRECT_URI: str
    EBAY_ENVIRONMENT: str = "sandbox"  # sandbox or production
    EBAY_MOCK_MODE: bool = False  # Use mock data instead of real API calls

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Data Sync Settings
    SYNC_BATCH_SIZE: int = 100
    MAX_ITEMS_PER_ACCOUNT: int = 2000

    # Timezone
    TZ: str = "Asia/Tokyo"

    # eBay API Endpoints (auto-configured based on environment)
    @property
    def EBAY_OAUTH_BASE_URL(self) -> str:
        if self.EBAY_ENVIRONMENT == "production":
            return "https://api.ebay.com"
        return "https://api.sandbox.ebay.com"

    @property
    def EBAY_AUTH_URL(self) -> str:
        if self.EBAY_ENVIRONMENT == "production":
            return "https://auth.ebay.com/oauth2/authorize"
        return "https://auth.sandbox.ebay.com/oauth2/authorize"

    @property
    def EBAY_TOKEN_URL(self) -> str:
        return f"{self.EBAY_OAUTH_BASE_URL}/identity/v1/oauth2/token"

    @property
    def EBAY_TRADING_API_URL(self) -> str:
        if self.EBAY_ENVIRONMENT == "production":
            return "https://api.ebay.com/ws/api.dll"
        return "https://api.sandbox.ebay.com/ws/api.dll"

    @property
    def EBAY_INVENTORY_API_URL(self) -> str:
        return f"{self.EBAY_OAUTH_BASE_URL}/sell/inventory/v1"

    @property
    def EBAY_ANALYTICS_API_URL(self) -> str:
        return f"{self.EBAY_OAUTH_BASE_URL}/sell/analytics/v1"

    @property
    def EBAY_FEED_API_URL(self) -> str:
        return f"{self.EBAY_OAUTH_BASE_URL}/sell/feed/v1"

    # Required scopes for eBay OAuth
    EBAY_SCOPES: List[str] = [
        "https://api.ebay.com/oauth/api_scope/sell.inventory",
        "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
        "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
