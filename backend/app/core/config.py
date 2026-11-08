"""Application settings and environment configuration."""

from typing import List, Optional, Any, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Creator Studio AI Global Configuration."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General Application
    APP_NAME: str = "Creator Studio AI"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_VERSION: str = "0.1.0"

    # Security
    APP_MASTER_ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    APP_SECRET_KEY: str = "insecure-dev-secret-key-change-in-production"
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://alikhan14756.github.io",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(i).strip().rstrip("/") for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip().rstrip("/") for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(i).strip().rstrip("/") for i in v if str(i).strip()]
        return ["http://localhost:3000", "http://127.0.0.1:3000", "https://alikhan14756.github.io"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/creator_studio_ai"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/creator_studio_ai"
    DB_POOL_SIZE: int = 4
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_TIMEOUT: int = 30

    # Supabase Auth
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None

    # AI Provider (Google Gemini)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_FAST: str = "gemini-1.5-flash"
    GEMINI_MODEL_REASONING: str = "gemini-1.5-pro"
    MAX_MONTHLY_SPEND_USD: float = 0.00
    MAX_DAILY_SPEND_USD: float = 0.00
    FREE_TIER_RPM_LIMIT: int = 15
    FREE_TIER_RPD_LIMIT: int = 1500

    # YouTube Data API & OAuth
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8000/api/v1/youtube/oauth/callback"
    YOUTUBE_UPLOAD_ENABLED: bool = True
    YOUTUBE_USE_MOCK: bool = True
    YOUTUBE_UPLOAD_CHUNK_SIZE: int = 8 * 1024 * 1024  # 8MB chunk size (must be multiple of 256KB)
    YOUTUBE_DAILY_UPLOAD_LIMIT: int = 4

    # Web Search Provider
    SEARCH_PROVIDER: str = "duckduckgo"
    TAVILY_API_KEY: Optional[str] = None

    # Audio & Voice Engine
    TTS_ENGINE: str = "edge-tts"
    TTS_DEFAULT_VOICE: str = "en-US-ChristopherNeural"
    TTS_SPEAKING_RATE: str = "+5%"

    # Job Queue & Background Worker
    WORKER_ID: Optional[str] = None
    WORKER_POLL_INTERVAL: float = 2.0
    WORKER_LEASE_SECONDS: int = 120
    WORKER_HEARTBEAT_INTERVAL: float = 10.0
    WORKER_DEFAULT_MAX_RETRIES: int = 3
    WORKER_BASE_BACKOFF_SECONDS: int = 30

    # Storage
    STORAGE_DRIVER: str = "local"
    LOCAL_STORAGE_DIR: str = "./storage"
    CLOUDFLARE_R2_ACCOUNT_ID: Optional[str] = None
    CLOUDFLARE_R2_ACCESS_KEY_ID: Optional[str] = None
    CLOUDFLARE_R2_SECRET_ACCESS_KEY: Optional[str] = None
    CLOUDFLARE_R2_BUCKET_NAME: str = "creator-studio-ai"

    # Video Production & Editing
    FFMPEG_PATH: Optional[str] = None
    FFPROBE_PATH: Optional[str] = None
    VIDEO_RENDERER_DEFAULT_MODE: str = "auto"  # auto, ffmpeg, mock
    VIDEO_OUTPUT_DIR: str = "./storage/renders"
    SUBTITLES_OUTPUT_DIR: str = "./storage/subtitles"
    VIDEO_DEFAULT_FPS: int = 30
    VIDEO_DEFAULT_RESOLUTION: str = "1080p"
    VIDEO_AUDIO_DUCKING_DB: float = -6.0
    VIDEO_MUSIC_DEFAULT_VOLUME: float = 0.15

    # Thumbnail Studio & SEO Engine
    THUMBNAIL_OUTPUT_DIR: str = "./storage/thumbnails"
    THUMBNAIL_DEFAULT_WIDTH: int = 1280
    THUMBNAIL_DEFAULT_HEIGHT: int = 720
    THUMBNAIL_MAX_FILE_SIZE_BYTES: int = 2097152  # 2MB
    SEO_TITLE_MAX_LENGTH: int = 95
    SEO_TAGS_MAX_CHARS: int = 500

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()
