import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

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
    """Authenticate via Supabase Auth and return the session token."""
    supabase = get_supabase()
    try:
        response = await asyncio.to_thread(
            lambda: supabase.auth.sign_in_with_password(
                {"email": body.email, "password": body.password}
            )
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    if not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = response.user
    session = response.session
    name = (user.user_metadata or {}).get("name") or (user.user_metadata or {}).get("full_name") or user.email

    return LoginResponse(
        access_token=session.access_token,
        token_type="bearer",
        user={
            "id": str(user.id),
            "email": user.email,
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
