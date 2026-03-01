import httpx
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_supabase
from app.core.security import get_current_user, TokenData

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """
    Authenticate the user.

    Strategy:
    1. Try Supabase GoTrue REST API first (proper auth flow).
    2. If GoTrue is unavailable (500 / network error), fall back to
       verifying the password directly against auth.users via the
       service-role client and issuing our own JWT.
    """
    # ── Attempt 1: Supabase GoTrue ──────────────────────────────────────
    try:
        url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json={"email": body.email, "password": body.password},
                timeout=10,
            )

        if response.status_code == 200:
            data = response.json()
            user_meta = data.get("user", {}).get("user_metadata") or {}
            name = user_meta.get("name") or user_meta.get("full_name") or data["user"]["email"]
            return LoginResponse(
                access_token=data["access_token"],
                token_type="bearer",
                user={
                    "id": data["user"]["id"],
                    "email": data["user"]["email"],
                    "name": name,
                },
            )

        # If GoTrue returned a real auth error (400/401), surface it
        if response.status_code < 500:
            try:
                detail = (
                    response.json().get("msg")
                    or response.json().get("error_description")
                    or "Invalid email or password"
                )
            except Exception:
                detail = "Invalid email or password"
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    except httpx.HTTPError:
        pass  # network / timeout — fall through to fallback
    except HTTPException:
        raise  # re-raise real 401s

    # ── Attempt 2: Direct DB password check (fallback) ──────────────────
    sb = get_supabase()

    # Verify email + password via pgcrypto crypt()
    result = sb.rpc(
        "verify_user_password",
        {"p_email": body.email, "p_password": body.password},
    ).execute()

    if not result.data or not result.data[0].get("is_valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    row = result.data[0]
    user_id = row["id"]
    email = row["email"]
    name = row.get("name") or email.split("@")[0]

    # Issue a JWT identical in shape to what Supabase would issue
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={"id": user_id, "email": email, "name": name},
    )


@router.post("/logout")
async def logout():
    """Client should discard the stored token on logout."""
    return {"message": "Logged out successfully"}


@router.get("/me")
async def me(current_user: TokenData = Depends(get_current_user)):
    """Return the currently authenticated user from their JWT."""
    return {
        "id": str(current_user.user_id),
        "email": current_user.email,
    }

