from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Firebase
    FIREBASE_ADMIN_SDK_PATH: str = "firebase-admin-sdk.json"
    
    # Storage paths
    STORAGE_PATH: str = "./storage"
    UPLOADS_PATH: str = "./uploads"
    TEMP_PATH: str = "./temp"
    
    # File limits
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Whisper model
    WHISPER_MODEL: str = "base"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()