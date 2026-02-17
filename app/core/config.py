"""Application configuration using Pydantic settings"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "STRATYON"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "stratyon_db"

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL for SQLAlchemy"""
        url = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        print(f"DEBUG: Computed DATABASE_URL: {url}")
        return url

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Construct synchronous database URL for Alembic migrations"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis (used for caching only)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_REFRESH_TOKENS_PER_USER: int = 5

    # Caching
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_GEOINT_TTL: int = 900  # 15 minutes (aggressive for performance)
    CACHE_USER_TTL: int = 600  # 10 minutes
    CACHE_KEYWORD_TTL: int = 300  # 5 minutes
    CACHE_COMPETITOR_TTL: int = 600  # 10 minutes

    # CORS - Override via CORS_ORIGINS env var for production
    # Example: CORS_ORIGINS='["https://app.yourdomain.com"]'
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # External APIs - AI/LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # External APIs - SEO & Analytics
    DATAFORSEO_LOGIN: Optional[str] = None
    DATAFORSEO_PASSWORD: Optional[str] = None

    # External APIs - Advertising
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = None
    GOOGLE_ADS_CLIENT_ID: Optional[str] = None
    GOOGLE_ADS_CLIENT_SECRET: Optional[str] = None
    GOOGLE_ADS_REFRESH_TOKEN: Optional[str] = None
    GOOGLE_ADS_CUSTOMER_ID: Optional[str] = None

    META_ACCESS_TOKEN: Optional[str] = None
    META_APP_ID: Optional[str] = None
    META_APP_SECRET: Optional[str] = None
    META_AD_ACCOUNT_ID: Optional[str] = None

    # External APIs - Mapping
    MAPBOX_ACCESS_TOKEN: Optional[str] = None

    # Feature flags
    ENABLE_GEOINT: bool = True
    ENABLE_STRATEGY_AI: bool = True
    ENABLE_COMPETITOR_TRACKING: bool = True
    ENABLE_MEDIA_MONITORING: bool = True

    # Competitor comparison test mode
    # When True, only queries Istanbul (34), Ankara (06), Izmir (35) instead of all 81 provinces
    COMPETITOR_TEST_MODE: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Clear cache to pick up any environment changes
get_settings.cache_clear()
settings = get_settings()
