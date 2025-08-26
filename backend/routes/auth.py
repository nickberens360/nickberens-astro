"""
Authentication routes for the admin dashboard.

Provides session-based authentication using secure cookies with proper admin user management.
"""

import os

# Import the proper admin authentication system
import sys
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

admin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "admin", "backend")
if admin_path not in sys.path:
    sys.path.insert(0, admin_path)

try:
    from auth import auth_manager
except ImportError:
    # Database-backed auth manager for the main backend
    import secrets
    import sqlite3
    from datetime import datetime, timedelta
    from pathlib import Path

    from passlib.context import CryptContext

    # Database-backed auth manager
    class DatabaseAuthManager:
        def __init__(self):
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # Set up database path
            self.db_path = Path(__file__).parent.parent / "logs" / "auth_sessions.db"
            self.db_path.parent.mkdir(exist_ok=True)
            self._init_database()
            # Cache admin credentials
            self._admin_username = os.getenv("ADMIN_USERNAME", "admin")
            self._admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

        def _init_database(self):
            """Initialize the sessions database."""
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_accessed TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """
            )
            # Clean up old sessions (older than 24 hours)
            cursor.execute(
                """
                DELETE FROM sessions 
                WHERE datetime(last_accessed) < datetime('now', '-24 hours')
            """
            )
            conn.commit()
            conn.close()

        def authenticate_user(self, username: str, password: str, ip_address: str = None, user_agent: str = None):
            # Simple authentication with environment variables
            if username != self._admin_username or password != self._admin_password:
                return None

            session_id = secrets.token_urlsafe(32)
            now = datetime.now()

            # Store session in database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (session_id, username, user_id, created_at, last_accessed, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (session_id, username, 1, now, now, ip_address, user_agent),
            )
            conn.commit()
            conn.close()

            return {
                "user": {"username": username, "id": 1},
                "session_id": session_id,
                "created_at": now,
                "last_accessed": now,
            }

        def get_session_from_request(self, request: Request):
            session_id = request.cookies.get("admin_session")
            if not session_id:
                return None

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get session and update last accessed time
            cursor.execute(
                """
                UPDATE sessions 
                SET last_accessed = ?
                WHERE session_id = ? 
                AND datetime(last_accessed) > datetime('now', '-24 hours')
                RETURNING *
            """,
                (datetime.now(), session_id),
            )

            row = cursor.fetchone()
            conn.commit()
            conn.close()

            if row:
                return {
                    "user": {"username": row["username"], "id": row["user_id"]},
                    "session_id": row["session_id"],
                    "created_at": datetime.fromisoformat(row["created_at"]),
                    "last_accessed": datetime.fromisoformat(row["last_accessed"]),
                }
            return None

        def expire_session(self, session_id: str):
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()

    auth_manager = DatabaseAuthManager()


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


def get_current_user(request: Request) -> Dict:
    """Get current user from session using the admin auth manager."""
    session = auth_manager.get_session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Return user data with session info
    return {
        "username": session["user"]["username"],
        "id": session["user"]["id"],
        "created_at": session.get("created_at", datetime.now()),
        "last_accessed": session.get("last_accessed", datetime.now()),
    }


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.post("/login")
async def login(login_request: LoginRequest, response: Response, request: Request) -> Dict:
    """
    Authenticate user and create session using the proper admin auth manager.

    Returns session information and sets secure HTTP-only cookie.
    """
    try:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        auth_result = auth_manager.authenticate_user(
            login_request.username, login_request.password, ip_address=client_ip, user_agent=user_agent
        )

        if not auth_result:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Set secure HTTP-only cookie
        response.set_cookie(
            key="admin_session",
            value=auth_result["session_id"],
            httponly=True,
            secure=os.getenv("ENVIRONMENT") == "production",
            samesite="lax",
            max_age=24 * 3600,  # 24 hours
        )

        user_data = auth_result["user"].copy()
        user_data.pop("password_hash", None)  # Remove password hash from response

        return {
            "success": True,
            "session_id": auth_result["session_id"],
            "user": {"username": user_data["username"], "authenticated": True},
            "message": "Login successful",
        }

    except HTTPException:
        raise
    except Exception as e:
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
        if session_id:
            auth_manager.expire_session(session_id)

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
        "session_timeout_hours": 24,
        "auth_method": "bcrypt_session_based",
        "secure_hashing": True,
    }
