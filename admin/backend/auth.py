"""
Authentication utilities for the admin dashboard.
"""

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import HTTPException, Request
from passlib.context import CryptContext
from passlib.hash import bcrypt

from .database import db_manager
from .models import AdminSession, AdminUser


class AuthManager:
    """Handles authentication, password hashing, and session management."""

    def __init__(self):
        # Password hashing context using bcrypt
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # Session expiry time (24 hours)
        self.session_expiry_hours = 24

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_session(self, user_id: int, ip_address: str = None, user_agent: str = None) -> str:
        """Create a new session for a user."""
        session_id = str(uuid.uuid4())
        now = datetime.now()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_sessions (id, user_id, started_at, last_active_at, ip_address, user_agent, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, now, now, ip_address, user_agent, True),
            )
            conn.commit()

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data if valid and active."""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, u.id as user_id, u.username, u.email, u.role, u.is_active as user_active
                FROM admin_sessions s
                JOIN admin_users u ON s.user_id = u.id
                WHERE s.id = ? AND s.is_active = 1 AND u.is_active = 1
                """,
                (session_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            session_data = dict(row)

            # Check if session is expired
            last_active = datetime.fromisoformat(session_data["last_active_at"])
            expiry_time = last_active + timedelta(hours=self.session_expiry_hours)

            if datetime.now() > expiry_time:
                # Expire the session
                self.expire_session(session_id)
                return None

            return session_data

    def update_session_activity(self, session_id: str):
        """Update the last activity time for a session."""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_sessions SET last_active_at = ? WHERE id = ?", (datetime.now(), session_id))
            conn.commit()

    def expire_session(self, session_id: str):
        """Expire a session."""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE id = ?", (session_id,))
            conn.commit()

    def expire_user_sessions(self, user_id: int):
        """Expire all sessions for a user."""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
            conn.commit()

    def authenticate_user(
        self, username: str, password: str, ip_address: str = None, user_agent: str = None
    ) -> Optional[Dict]:
        """Authenticate a user and create a session."""
        user = db_manager.get_admin_user(username)

        if not user or not self.verify_password(password, user["password_hash"]):
            return None

        # Update last login time
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_users SET last_login_at = ? WHERE id = ?", (datetime.now(), user["id"]))
            conn.commit()

        # Create session
        session_id = self.create_session(user["id"], ip_address, user_agent)

        return {"user": user, "session_id": session_id}

    def create_admin_user(self, username: str, password: str, email: str = None, role: str = "viewer") -> int:
        """Create a new admin user."""
        password_hash = self.hash_password(password)
        return db_manager.create_admin_user(username, email, password_hash, role)

    def get_session_from_request(self, request: Request) -> Optional[Dict]:
        """Extract and validate session from request."""
        # Try to get session ID from cookie
        session_id = request.cookies.get("admin_session")

        # Fallback to Authorization header
        if not session_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_id = auth_header.split(" ")[1]

        if not session_id:
            return None

        session = self.get_session(session_id)
        if session:
            # Update activity
            self.update_session_activity(session_id)

        return session

    def cleanup_expired_sessions(self):
        """Clean up expired sessions from the database."""
        expiry_cutoff = datetime.now() - timedelta(hours=self.session_expiry_hours)

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE last_active_at < ?", (expiry_cutoff,))
            conn.commit()


# Global auth manager instance
auth_manager = AuthManager()


def require_auth(request: Request):
    """Dependency to require authentication for routes."""
    session = auth_manager.get_session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def require_admin_role(request: Request):
    """Dependency to require admin role for routes."""
    session = require_auth(request)
    if session["role"] not in ["admin", "owner"]:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return session


def get_current_user(request: Request) -> Optional[Dict]:
    """Get current user from request if authenticated, None otherwise."""
    return auth_manager.get_session_from_request(request)
