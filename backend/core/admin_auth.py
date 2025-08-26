"""
Admin authentication system for the main backend.
Migrated from admin/backend/auth.py with improvements.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import bcrypt
from fastapi import HTTPException, Request

from .admin_database import admin_db_manager

logger = logging.getLogger(__name__)


class AdminAuthManager:
    """Handles admin authentication, password hashing, and session management."""

    def __init__(self):
        # Use bcrypt directly instead of passlib to avoid version compatibility issues
        self._bcrypt_rounds = 12
        # Session expiry time (24 hours)
        self.session_expiry_hours = 24
        # Rate limiting for failed attempts
        self._failed_attempts = {}
        self._lockout_duration = 300  # 5 minutes lockout

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with validation."""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        try:
            password_bytes = password.encode("utf-8")
            salt = bcrypt.gensalt(rounds=self._bcrypt_rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            return hashed.decode("utf-8")
        except Exception as e:
            logger.error(f"Bcrypt hashing failed: {str(e)}", exc_info=True)
            raise ValueError("Failed to hash password")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash with rate limiting."""
        if not plain_password or not hashed_password:
            return False

        try:
            # Try bcrypt directly first (works for both old and new hashes)
            password_bytes = plain_password.encode("utf-8")
            hash_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}", exc_info=True)
            return False

    def create_session(self, user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Create a new session for a user with validation."""
        if user_id <= 0:
            raise ValueError("Invalid user ID")

        # Clean up expired sessions before creating new one
        self.cleanup_expired_sessions()

        session_id = str(uuid.uuid4())
        now = datetime.now()

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Limit concurrent sessions per user (max 5)
                cursor.execute("SELECT COUNT(*) FROM admin_sessions WHERE user_id = ? AND is_active = 1", (user_id,))
                active_sessions = cursor.fetchone()[0]

                if active_sessions >= 5:
                    # Expire oldest session - SQLite doesn't support ORDER BY in UPDATE, so use subquery
                    cursor.execute(
                        """
                        UPDATE admin_sessions 
                        SET is_active = 0 
                        WHERE id = (
                            SELECT id FROM admin_sessions 
                            WHERE user_id = ? AND is_active = 1 
                            ORDER BY started_at ASC 
                            LIMIT 1
                        )
                        """,
                        (user_id,),
                    )

                cursor.execute(
                    """
                    INSERT INTO admin_sessions (id, user_id, started_at, last_active_at, ip_address, user_agent, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, user_id, now, now, ip_address, user_agent[:500] if user_agent else None, True),
                )

                logger.info(f"Created session {session_id} for user {user_id}")
                return session_id

        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {str(e)}", exc_info=True)
            raise

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data if valid and active with enhanced validation."""
        if not session_id or not session_id.strip():
            return None

        try:
            # Validate UUID format
            uuid.UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id[:8]}...")
            return None

        try:
            with admin_db_manager.get_connection() as conn:
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

        except Exception as e:
            logger.error(f"Error getting session {session_id[:8]}...: {str(e)}", exc_info=True)
            return None

    def update_session_activity(self, session_id: str) -> None:
        """Update the last activity time for a session."""
        if not session_id:
            return

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_sessions SET last_active_at = ? WHERE id = ? AND is_active = 1",
                    (datetime.now(), session_id),
                )
        except Exception as e:
            logger.error(f"Error updating session activity {session_id[:8]}...: {str(e)}", exc_info=True)

    def expire_session(self, session_id: str) -> None:
        """Expire a session safely."""
        if not session_id:
            return

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE id = ?", (session_id,))
                logger.info(f"Expired session {session_id[:8]}...")
        except Exception as e:
            logger.error(f"Error expiring session {session_id[:8]}...: {str(e)}", exc_info=True)

    def expire_user_sessions(self, user_id: int) -> None:
        """Expire all sessions for a user."""
        if user_id <= 0:
            return

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
                logger.info(f"Expired all sessions for user {user_id}")
        except Exception as e:
            logger.error(f"Error expiring sessions for user {user_id}: {str(e)}", exc_info=True)

    def authenticate_user(
        self, username: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Optional[Dict]:
        """Authenticate a user and create a session with rate limiting."""
        if not username or not password:
            return None

        username = username.strip().lower()

        # Check for rate limiting
        if self._is_rate_limited(ip_address or "unknown"):
            logger.warning(f"Rate limited authentication attempt from {ip_address} for user {username}")
            return None

        user = admin_db_manager.get_admin_user(username)

        if not user or not self.verify_password(password, user["password_hash"]):
            self._record_failed_attempt(ip_address or "unknown")
            logger.warning(f"Failed authentication attempt for user {username} from {ip_address}")
            return None

        # Reset failed attempts on successful login
        self._reset_failed_attempts(ip_address or "unknown")

        try:
            # Update last login time
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE admin_users SET last_login_at = ? WHERE id = ?", (datetime.now(), user["id"]))

            # Create session
            session_id = self.create_session(user["id"], ip_address, user_agent)

            logger.info(f"Successful authentication for user {username}")
            return {"user": user, "session_id": session_id}

        except Exception as e:
            logger.error(f"Error during authentication for user {username}: {str(e)}", exc_info=True)
            return None

    def create_admin_user(self, username: str, password: str, email: Optional[str] = None, role: str = "viewer") -> int:
        """Create a new admin user with validation."""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        password_hash = self.hash_password(password)
        return admin_db_manager.create_admin_user(username, email, password_hash, role)

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

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions from the database."""
        try:
            expiry_cutoff = datetime.now() - timedelta(hours=self.session_expiry_hours)

            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_sessions SET is_active = 0 WHERE last_active_at < ? AND is_active = 1",
                    (expiry_cutoff,),
                )
                expired_count = cursor.rowcount
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired sessions")
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}", exc_info=True)

    def _is_rate_limited(self, ip_address: str) -> bool:
        """Check if IP is rate limited."""
        now = datetime.now()
        if ip_address in self._failed_attempts:
            attempts, last_attempt = self._failed_attempts[ip_address]
            if attempts >= 5 and (now - last_attempt).total_seconds() < self._lockout_duration:
                return True
            elif (now - last_attempt).total_seconds() >= self._lockout_duration:
                # Reset after lockout period
                del self._failed_attempts[ip_address]
        return False

    def _record_failed_attempt(self, ip_address: str) -> None:
        """Record a failed authentication attempt."""
        now = datetime.now()
        if ip_address in self._failed_attempts:
            attempts, _ = self._failed_attempts[ip_address]
            self._failed_attempts[ip_address] = (attempts + 1, now)
        else:
            self._failed_attempts[ip_address] = (1, now)

    def _reset_failed_attempts(self, ip_address: str) -> None:
        """Reset failed attempts for IP."""
        if ip_address in self._failed_attempts:
            del self._failed_attempts[ip_address]


# Global auth manager instance
admin_auth_manager = AdminAuthManager()


def require_admin_auth(request: Request) -> Dict:
    """Dependency to require authentication for admin routes."""
    session = admin_auth_manager.get_session_from_request(request)
    if not session:
        logger.warning(f"Unauthenticated admin request from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def require_admin_role(request: Request) -> Dict:
    """Dependency to require admin role for routes with logging."""
    session = require_admin_auth(request)
    if session["role"] not in ["admin", "owner"]:
        logger.warning(f"Unauthorized admin access attempt by user {session.get('username', 'unknown')}")
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return session


def get_current_admin_user(request: Request) -> Optional[Dict]:
    """Get current admin user from request if authenticated, None otherwise."""
    try:
        return admin_auth_manager.get_session_from_request(request)
    except Exception as e:
        logger.error(f"Error getting current admin user: {str(e)}", exc_info=True)
        return None
