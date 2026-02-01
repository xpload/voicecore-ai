"""
Configuration management for VoiceCore AI system.

This module handles all environment variables and application settings
with proper validation and type safety using Pydantic Settings.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application Settings
    app_name: str = Field(default="VoiceCore AI", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Database Configuration
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(default=None, env="SUPABASE_ANON_KEY")
    supabase_service_role_key: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Twilio Configuration
    twilio_account_sid: Optional[str] = Field(default=None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, env="TWILIO_PHONE_NUMBER")
    twilio_webhook_url: str = Field(default="http://localhost:8000/api/webhooks/twilio", env="TWILIO_WEBHOOK_URL")
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_realtime_model: str = Field(
        default="gpt-4o-realtime-preview", 
        env="OPENAI_REALTIME_MODEL"
    )
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Security Settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, 
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"], 
        env="ALLOWED_ORIGINS"
    )
    
    # File Storage
    storage_bucket: str = Field(default="voicecore-recordings", env="STORAGE_BUCKET")
    max_file_size_mb: int = Field(default=100, env="MAX_FILE_SIZE_MB")
    
    # Rate Limiting
    rate_limit_calls_per_minute: int = Field(
        default=60, 
        env="RATE_LIMIT_CALLS_PER_MINUTE"
    )
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # WebSocket Configuration
    websocket_heartbeat_interval: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    websocket_timeout: int = Field(default=60, env="WEBSOCKET_TIMEOUT")
    
    # Call Configuration
    max_concurrent_calls_per_tenant: int = Field(default=1000, env="MAX_CONCURRENT_CALLS_PER_TENANT")
    call_timeout_seconds: int = Field(default=3600, env="CALL_TIMEOUT_SECONDS")
    ai_response_timeout_ms: int = Field(default=2000, env="AI_RESPONSE_TIMEOUT_MS")
    
    # Spam Detection
    spam_detection_threshold: float = Field(default=0.7, env="SPAM_DETECTION_THRESHOLD")
    spam_challenge_enabled: bool = Field(default=True, env="SPAM_CHALLENGE_ENABLED")
    
    # Monitoring & Logging
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    
    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is supported."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("twilio_phone_number")
    def validate_phone_number(cls, v):
        """Validate Twilio phone number format."""
        if v and not v.startswith("+"):
            raise ValueError("Twilio phone number must start with +")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


class TenantSettings(BaseSettings):
    """Tenant-specific configuration settings."""
    
    # AI Configuration
    ai_name: str = Field(default="Sofia", description="AI receptionist name")
    ai_gender: str = Field(default="female", description="AI voice gender")
    ai_voice_id: str = Field(default="alloy", description="OpenAI voice ID")
    ai_language: str = Field(default="auto", description="Primary language")
    
    # Company Information
    company_name: str = Field(..., description="Company name")
    company_domain: str = Field(default="", description="Company domain")
    
    # Call Handling
    max_transfer_attempts: int = Field(default=3, description="Max AI attempts before transfer")
    default_department: str = Field(default="customer_service", description="Default transfer department")
    
    # Business Hours
    business_hours_start: str = Field(default="09:00", description="Business hours start (HH:MM)")
    business_hours_end: str = Field(default="17:00", description="Business hours end (HH:MM)")
    timezone: str = Field(default="UTC", description="Company timezone")
    
    # Features
    enable_spam_detection: bool = Field(default=True, description="Enable spam detection")
    enable_call_recording: bool = Field(default=True, description="Enable call recording")
    enable_transcription: bool = Field(default=True, description="Enable call transcription")
    enable_emotion_detection: bool = Field(default=False, description="Enable emotion detection")
    
    # Credit System
    monthly_credit_limit: int = Field(default=1000, description="Monthly call minutes limit")
    credit_warning_threshold: int = Field(default=100, description="Low credit warning threshold")
    
    @validator("ai_gender")
    def validate_ai_gender(cls, v):
        """Validate AI gender selection."""
        valid_genders = ["male", "female"]
        if v.lower() not in valid_genders:
            raise ValueError(f"AI gender must be one of: {valid_genders}")
        return v.lower()
    
    @validator("ai_voice_id")
    def validate_voice_id(cls, v):
        """Validate OpenAI voice ID."""
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if v.lower() not in valid_voices:
            raise ValueError(f"Voice ID must be one of: {valid_voices}")
        return v.lower()
    
    class Config:
        case_sensitive = False