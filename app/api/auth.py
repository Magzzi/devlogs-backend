import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
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
    """Authenticate via Supabase Auth REST API using the anon key."""
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

    if response.status_code != 200:
        # Surface the actual Supabase error to help diagnose issues
        try:
            detail = response.json().get("msg") or response.json().get("error_description") or "Invalid email or password"
        except Exception:
            detail = "Invalid email or password"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

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

