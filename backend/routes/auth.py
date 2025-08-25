"""
Authentication routes for the admin dashboard.

Provides session-based authentication using secure cookies with simple admin user management.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Simple in-memory session store (in production, use Redis or database)
active_sessions: Dict[str, Dict] = {}
SESSION_TIMEOUT_HOURS = 24

# Default admin credentials (should be configured via environment variables)
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "admin"


def get_admin_credentials() -> tuple[str, str]:
    """Get admin credentials from environment or use defaults."""
    username = os.getenv("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME)
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    return username, password


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with a salt."""
    salt = os.getenv("PASSWORD_SALT", "admin_dashboard_salt")
    return hashlib.sha256((password + salt).encode()).hexdigest()


def verify_password(password: str, expected_username: str) -> bool:
    """Verify password for the given user."""
    admin_username, admin_password = get_admin_credentials()

    if expected_username != admin_username:
        return False

    return hmac.compare_digest(hash_password(password), hash_password(admin_password))


def create_session(username: str) -> str:
    """Create a new session and return session ID."""
    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = {"username": username, "created_at": datetime.now(), "last_accessed": datetime.now()}
    return session_id


def get_session(session_id: str) -> Optional[Dict]:
    """Get session data if valid and not expired."""
    if session_id not in active_sessions:
        return None

    session = active_sessions[session_id]

    # Check if session has expired
    if datetime.now() - session["last_accessed"] > timedelta(hours=SESSION_TIMEOUT_HOURS):
        del active_sessions[session_id]
        return None

    # Update last accessed time
    session["last_accessed"] = datetime.now()
    return session


def get_current_user(request: Request) -> Dict:
    """Get current user from session cookie."""
    session_id = request.cookies.get("admin_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.post("/login")
async def login(request: LoginRequest, response: Response) -> Dict:
    """
    Authenticate user and create session.

    Returns session information and sets secure HTTP-only cookie.
    """
    try:
        # Debug logging
        print(f"Login attempt - Username: '{request.username}', Password: '{request.password}'")
        admin_username, admin_password = get_admin_credentials()
        print(f"Expected - Username: '{admin_username}', Password: '{admin_password}'")

        if not verify_password(request.password, request.username):
            print("Password verification failed")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        print("Password verification successful")

        # Create session
        session_id = create_session(request.username)

        # Set secure HTTP-only cookie
        response.set_cookie(
            key="admin_session",
            value=session_id,
            httponly=True,
            secure=os.getenv("ENVIRONMENT") == "production",
            samesite="lax",
            max_age=SESSION_TIMEOUT_HOURS * 3600,
        )

        return {
            "success": True,
            "session_id": session_id,
            "user": {"username": request.username, "authenticated": True},
            "message": "Login successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login exception: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/me")
async def get_current_user_info(user: Dict = Depends(get_current_user)) -> Dict:
    """Get current user information."""
    return {
        "user": {
            "username": user["username"],
            "authenticated": True,
            "session_created": user["created_at"].isoformat(),
            "last_accessed": user["last_accessed"].isoformat(),
        }
    }


@router.post("/logout")
async def logout(request: Request, response: Response) -> Dict:
    """Logout user and invalidate session."""
    try:
        session_id = request.cookies.get("admin_session")
        if session_id and session_id in active_sessions:
            del active_sessions[session_id]

        # Clear cookie
        response.delete_cookie(key="admin_session")

        return {"success": True, "message": "Logged out successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, user: Dict = Depends(get_current_user)) -> Dict:
    """Change user password (currently not implemented for simple auth)."""
    # For this simple implementation, password changes aren't supported
    # In a real application, you'd update the stored password
    raise HTTPException(status_code=501, detail="Password changes not implemented for environment-based authentication")


@router.post("/create-user")
async def create_user(request: CreateUserRequest, user: Dict = Depends(get_current_user)) -> Dict:
    """Create new user (currently not implemented for simple auth)."""
    # For this simple implementation, user creation isn't supported
    # In a real application, you'd store the new user credentials
    raise HTTPException(status_code=501, detail="User creation not implemented for environment-based authentication")


@router.get("/status")
async def auth_status() -> Dict:
    """Get authentication system status."""
    return {
        "auth_enabled": True,
        "session_timeout_hours": SESSION_TIMEOUT_HOURS,
        "active_sessions": len(active_sessions),
        "auth_method": "session_based",
    }
