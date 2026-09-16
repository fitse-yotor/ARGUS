from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///storage/argus.db'
    storage_dir: Path = Path('storage')
    admin_username: str = 'admin'
    admin_password: str = ''
    model_path: str = 'storage/models/yolo11n.pt'
    device: str = 'cpu'
    upload_limit_mb: int = 1024
    session_hours: int = 8
    cookie_secure: bool = False
    demo_enabled: bool = True

settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
