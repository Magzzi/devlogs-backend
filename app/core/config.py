from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DevLogs"
    DEBUG: bool = True

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # JWT — copy from Supabase Dashboard → Project Settings → API → JWT Secret
    JWT_SECRET: str

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://developer-logs.vercel.app",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
