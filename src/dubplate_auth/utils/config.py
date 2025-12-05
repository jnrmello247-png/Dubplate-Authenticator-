"""
Configuration utilities for Dubplate Authenticator.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration."""
    
    # Database
    database_url: str = "sqlite:///dubplate_auth.db"
    
    # Audio processing
    sample_rate: int = 22050
    hop_length: int = 512
    
    # AI Detection
    ai_sensitivity: float = 0.7
    
    # Watermarking
    secret_key: str = "dubplate_auth_secret_key"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 5000
    debug: bool = False
    
    # File upload
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: tuple = (".wav", ".mp3", ".flac", ".ogg", ".m4a")
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            sample_rate=int(os.getenv("SAMPLE_RATE", cls.sample_rate)),
            hop_length=int(os.getenv("HOP_LENGTH", cls.hop_length)),
            ai_sensitivity=float(os.getenv("AI_SENSITIVITY", cls.ai_sensitivity)),
            secret_key=os.getenv("SECRET_KEY", cls.secret_key),
            api_host=os.getenv("API_HOST", cls.api_host),
            api_port=int(os.getenv("API_PORT", cls.api_port)),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            max_file_size=int(os.getenv("MAX_FILE_SIZE", cls.max_file_size)),
        )


def get_config() -> Config:
    """Get the application configuration."""
    return Config.from_env()
