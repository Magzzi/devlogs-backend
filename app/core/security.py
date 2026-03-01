from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
from uuid import UUID

from app.core.config import settings

_bearer = HTTPBearer()


class TokenData:
    def __init__(self, user_id: UUID, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenData:
    """Verify the Supabase JWT and return the authenticated user."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            # Supabase sets aud="authenticated"; skip audience check so the
            # same secret works whether the token was issued by the anon or
            # service-role key.
            options={"verify_aud": False},
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if not user_id:
            raise exc
        return TokenData(user_id=UUID(user_id), email=email)
    except JWTError:
        raise exc
