from fastapi import Depends
from typing import Optional
from uuid import UUID

from app.core.config import settings


class TokenData:
    def __init__(self, user_id: UUID, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


async def get_current_user() -> TokenData:
    """Mock dependency to get current authenticated user."""
    # Use a fixed valid UUID for demo purposes
    return TokenData(
        user_id=UUID("00000000-0000-0000-0000-000000000123"),
        email=settings.MOCK_USER_EMAIL
    )
