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


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class VerifyEmailRequest(BaseModel):
    token: str
    type: str = "signup"  # or "recovery", "magiclink"


class SetPasswordRequest(BaseModel):
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

    try:
        # Verify email + password via pgcrypto crypt()
        result = sb.rpc(
            "verify_user_password",
            {"p_email": body.email, "p_password": body.password},
        ).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Auth service is unavailable and the fallback verify_user_password "
                f"RPC function may not exist. Error: {e}"
            ),
        )

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


@router.post("/signup", response_model=LoginResponse)
async def signup(body: SignupRequest):
    """
    Register a new user with email/password.
    
    Flow:
    1. Create auth user via Supabase GoTrue API with email confirmation required
    2. Trigger automatically creates profile in public.users table
    3. Return tokens (user must verify email before full access)
    """
    try:
        url = f"{settings.SUPABASE_URL}/auth/v1/signup"
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
        
        # Prepare user metadata
        user_metadata = {}
        if body.display_name:
            user_metadata["display_name"] = body.display_name.strip()
            user_metadata["name"] = body.display_name.strip()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json={
                    "email": body.email,
                    "password": body.password,
                    "options": {
                        "data": user_metadata
                    }
                },
                timeout=10,
            )
        
        if response.status_code in (200, 201):
            data = response.json()
            user = data.get("user", {})
            session = data.get("session")
            
            # Extract user info
            user_meta = user.get("user_metadata") or {}
            name = (
                user_meta.get("display_name") 
                or user_meta.get("name") 
                or user_meta.get("full_name") 
                or user["email"].split("@")[0]
            )
            
            # Return session tokens if available (auto-confirm might be enabled)
            # Otherwise return a temporary token
            if session and session.get("access_token"):
                access_token = session["access_token"]
            else:
                # Generate temporary token for email verification flow
                now = datetime.now(timezone.utc)
                payload = {
                    "sub": user["id"],
                    "email": user["email"],
                    "aud": "authenticated",
                    "role": "authenticated",
                    "iat": int(now.timestamp()),
                    "exp": int((now + timedelta(hours=1)).timestamp()),
                }
                access_token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
            
            return LoginResponse(
                access_token=access_token,
                token_type="bearer",
                user={
                    "id": user["id"],
                    "email": user["email"],
                    "name": name,
                    "email_confirmed": user.get("email_confirmed_at") is not None
                },
            )
        
        # Handle errors from Supabase
        if response.status_code >= 400:
            try:
                error_data = response.json()
                detail = (
                    error_data.get("msg")
                    or error_data.get("error_description") 
                    or error_data.get("message")
                    or "Signup failed"
                )
            except Exception:
                detail = "Signup failed"
            
            # Map specific error codes
            if response.status_code == 422 or "already registered" in detail.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth service unavailable: {str(e)}"
        )


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest):
    """
    Verify email with token from confirmation email.
    
    Supabase sends verification link like:
    http://your-site.com/auth/verify?token={token}&type=signup
    """
    try:
        url = f"{settings.SUPABASE_URL}/auth/v1/verify"
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json={
                    "token": body.token,
                    "type": body.type,
                },
                timeout=10,
            )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "message": "Email verified successfully",
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token")
            }
        
        # Handle errors
        try:
            error_data = response.json()
            detail = error_data.get("error_description") or error_data.get("message") or "Verification failed"
        except Exception:
            detail = "Verification failed"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Verification service unavailable: {str(e)}"
        )


@router.post("/resend-verification")
async def resend_verification(body: LoginRequest):
    """Resend email verification link."""
    try:
        url = f"{settings.SUPABASE_URL}/auth/v1/resend"
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json={
                    "type": "signup",
                    "email": body.email,
                },
                timeout=10,
            )
        
        if response.status_code == 200:
            return {"message": "Verification email sent"}
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resend verification email"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )


@router.post("/set-password")
async def set_password(
    body: SetPasswordRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Set password for OAuth users who don't have one.
    This allows OAuth users to also login with email/password.
    """
    try:
        # Use Supabase admin API to update user password
        url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{current_user.user_id}"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                headers=headers,
                json={
                    "password": body.password,
                    "user_metadata": {"has_password": True},
                },
                timeout=10,
            )
        
        if response.status_code == 200:
            return {"message": "Password set successfully"}
        
        # Handle errors
        try:
            error_data = response.json()
            detail = error_data.get("error_description") or error_data.get("message") or "Failed to set password"
        except Exception:
            detail = "Failed to set password"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )


@router.post("/logout")
async def logout():
    """Client should discard the stored token on logout."""
    return {"message": "Logged out successfully"}


@router.get("/me")
async def me(current_user: TokenData = Depends(get_current_user)):
    """Return the currently authenticated user from their JWT + public profile."""
    sb = get_supabase()
    # Fetch display name and email confirmation status from public.users
    name = None
    display_name = None
    email_confirmed = False
    has_password = False  # Default to False for OAuth users
    
    try:
        result = (
            sb.table("users")
            .select("name, display_name, email_confirmed_at")
            .eq("id", str(current_user.user_id))
            .maybe_single()
            .execute()
        )
        if result.data:
            name = result.data.get("name")
            display_name = result.data.get("display_name")
            email_confirmed = result.data.get("email_confirmed_at") is not None
    except Exception:
        pass
    
    # Check if user has email/password provider in identities
    try:
        identities = (
            sb.from_("auth.identities")
            .select("provider")
            .eq("user_id", str(current_user.user_id))
            .execute()
        )
        
        if identities.data:
            # User has password if 'email' provider exists
            has_password = any(
                identity.get("provider") == "email" 
                for identity in identities.data
            )
    except Exception:
        # Default to True to avoid blocking users if check fails
        has_password = True

    # Also check user_metadata for has_password flag (set when OAuth user adds a password)
    if not has_password:
        try:
            user_url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{current_user.user_id}"
            admin_headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            }
            import httpx as _httpx
            async with _httpx.AsyncClient() as client:
                user_resp = await client.get(user_url, headers=admin_headers, timeout=10)
            if user_resp.status_code == 200:
                user_data = user_resp.json()
                meta = user_data.get("user_metadata") or {}
                if meta.get("has_password"):
                    has_password = True
        except Exception:
            pass
    
    return {
        "id": str(current_user.user_id),
        "email": current_user.email,
        "name": name or "",
        "display_name": display_name or name or "",
        "email_confirmed": email_confirmed,
        "has_password": has_password,
    }


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    display_name: str | None = None


@router.patch("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Update the current user's display name in public.users."""
    sb = get_supabase()
    
    update_data = {}
    if body.name is not None:
        update_data["name"] = body.name.strip()
    if body.display_name is not None:
        update_data["display_name"] = body.display_name.strip()
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    try:
        result = (
            sb.table("users")
            .update(update_data)
            .eq("id", str(current_user.user_id))
            .execute()
        )
        if not result.data:
            # Row might not exist yet — upsert it
            upsert_data = {
                "id": str(current_user.user_id),
                "email": current_user.email or "",
                **update_data
            }
            sb.table("users").upsert(upsert_data).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {e}",
        )
    return {"message": "Profile updated", **update_data}

