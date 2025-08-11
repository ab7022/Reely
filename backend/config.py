from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv
import os


class Settings(BaseSettings):
    # Firebase
    FIREBASE_ADMIN_SDK_PATH: str = "reely.json"
    
    # Storage paths
    STORAGE_PATH: str = "./storage"
    UPLOADS_PATH: str = "./uploads"
    TEMP_PATH: str = "./temp"
    # Cache paths
    TRANSCRIPT_CACHE_PATH: str = "./cache/transcripts"
    
    # File limits
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Whisper model
    WHISPER_MODEL: str = "base"
    # FFmpeg binary (path or name on PATH)
    FFMPEG_BIN: str = "ffmpeg"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Simulation (fake processing) settings
    # When enabled (or when a request explicitly asks to simulate), the backend will
    # skip heavy media processing and instead advance steps over a fixed period so
    # the frontend can show progress even without FFmpeg / Whisper working locally.
    SIMULATE_PROCESSING: bool = False
    SIMULATED_TOTAL_SECONDS: int = 60  # Total time to spread across remaining steps
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Proactively load env from backend/.env and project root .env if present
_backend_env = Path(__file__).resolve().parent / ".env"
_root_env = Path(__file__).resolve().parents[1] / ".env"
for _env in (_backend_env, _root_env):
    if _env.exists():
        load_dotenv(dotenv_path=_env, override=False)

settings = Settings()

# Ensure paths are absolute (fixes issues when running server from project root)
_base_dir = Path(__file__).resolve().parent
for _path_attr in ["STORAGE_PATH", "UPLOADS_PATH", "TEMP_PATH", "TRANSCRIPT_CACHE_PATH"]:
    _p = getattr(settings, _path_attr, None)
    if isinstance(_p, str) and _p and not os.path.isabs(_p):
        abs_p = (_base_dir / _p).resolve()
        setattr(settings, _path_attr, str(abs_p))
        try:
            abs_p.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass