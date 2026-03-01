from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt
from jwt.exceptions import PyJWTError
from typing import Optional
from uuid import UUID

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)


class TokenData:
    def __init__(self, user_id: UUID, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenData:
    """Verify the Supabase JWT and return the authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # PyJWT uses JWT_SECRET as a raw UTF-8 string for HS256,
        # which matches how Supabase signs its tokens.
        payload = pyjwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if not user_id:
            raise exc
        return TokenData(user_id=UUID(user_id), email=email)
    except PyJWTError:
        raise exc
