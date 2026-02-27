from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DevLogs"
    DEBUG: bool = True
    
    # Mock User
    MOCK_USER_ID: str = "mock-user-123"
    MOCK_USER_EMAIL: str = "demo@devlogs.com"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "https://developer-logs.vercel.app"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
