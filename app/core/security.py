from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError
from typing import Optional
from uuid import UUID
from functools import lru_cache

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """Cached JWKS client for verifying Supabase GoTrue ES256 tokens."""
    jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, headers={"apikey": settings.SUPABASE_ANON_KEY})


class TokenData:
    def __init__(self, user_id: UUID, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


def _decode_token(token: str) -> dict:
    """
    Decode a JWT token.
    - ES256 tokens (from GoTrue): verified with Supabase JWKS public key
    - HS256 tokens (self-issued fallback): verified with JWT_SECRET
    """
    # Peek at the header to determine the algorithm
    header = pyjwt.get_unverified_header(token)
    alg = header.get("alg", "")

    if alg.startswith("ES") or alg.startswith("RS") or alg.startswith("PS"):
        # Asymmetric token — verify with JWKS public key
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return pyjwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            options={"verify_aud": False},
            leeway=30,  # allow 30s clock skew
        )
    else:
        # Symmetric (HS*) token — verify with JWT_SECRET
        return pyjwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256", "HS384", "HS512"],
            options={"verify_aud": False},
            leeway=30,
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenData:
    """Verify the JWT and return the authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = _decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(user_id=UUID(user_id), email=email)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT validation failed: {type(e).__name__}: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
