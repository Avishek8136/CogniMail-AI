"""
Application configuration management using Pydantic settings.
Handles environment variables and configuration validation.
"""

import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Main application settings."""
    
    # AI Configuration
    gemini_api_key: str
    ai_confidence_threshold: float = 0.7
    max_tokens: int = 1000
    temperature: float = 0.3
    
    # Google Workspace Configuration
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8080/callback"
    
    # Application Settings
    app_name: str = "AI Email Manager"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database Configuration
    database_path: str = "data/email_manager.db"
    
    # GUI Settings
    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator('gemini_api_key')
    def validate_gemini_api_key(cls, v):
        if not v or v == "your_gemini_api_key_here":
            raise ValueError("Valid Gemini API key is required")
        return v
    
    @validator('google_client_id')
    def validate_google_client_id(cls, v):
        if not v or v == "your_google_client_id_here":
            raise ValueError("Valid Google Client ID is required")
        return v
    
    @validator('google_client_secret')
    def validate_google_client_secret(cls, v):
        if not v or v == "your_google_client_secret_here":
            raise ValueError("Valid Google Client Secret is required")
        return v
    
    @validator('database_path')
    def ensure_database_directory_exists(cls, v):
        """Ensure the database directory exists."""
        db_path = Path(v)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)


# Global settings instance
settings = None

def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global settings
    if settings is None:
        try:
            settings = Settings()
        except Exception as e:
            # For development, create a mock settings object
            print(f"Warning: Could not load settings from .env: {e}")
            print("Using default settings for development")
            # You'll need to create a .env file with real values
            settings = None
    return settings

def initialize_settings(env_file: Optional[str] = None) -> Settings:
    """Initialize settings with optional custom env file."""
    global settings
    if env_file and os.path.exists(env_file):
        settings = Settings(_env_file=env_file)
    else:
        settings = Settings()
    return settings
