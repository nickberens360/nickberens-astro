"""
Admin database management for the main backend.
Migrated from admin/backend/database.py with improvements.
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AdminDatabaseManager:
    """Manages admin database operations with proper connection handling."""

    def __init__(self):
        """Initialize the admin database manager."""
        # Use backend/logs directory for admin database
        self.db_path = Path(__file__).parent.parent / "logs" / "admin_monitoring.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Admin users table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'viewer',
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login_at TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Admin sessions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_sessions (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        last_active_at TIMESTAMP NOT NULL,
                        ip_address TEXT,
                        user_agent TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES admin_users (id)
                    )
                """
                )

                # Admin settings table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE NOT NULL,
                        setting_value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_by INTEGER,
                        FOREIGN KEY (updated_by) REFERENCES admin_users (id)
                    )
                """
                )

                # Rate limiting table for persistent storage
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_limiting (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        identifier TEXT NOT NULL,  -- IP address or username
                        identifier_type TEXT NOT NULL,  -- 'ip' or 'username'
                        attempt_count INTEGER NOT NULL DEFAULT 1,
                        first_attempt_at TIMESTAMP NOT NULL,
                        last_attempt_at TIMESTAMP NOT NULL,
                        lockout_until TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(identifier, identifier_type)
                    )
                """
                )

                # Security events table for monitoring
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,  -- 'login_failure', 'lockout', 'suspicious_session', etc.
                        identifier TEXT NOT NULL,  -- IP address, username, or session_id
                        details TEXT,  -- JSON details
                        severity TEXT NOT NULL DEFAULT 'low',  -- 'low', 'medium', 'high', 'critical'
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 2FA (TOTP) table for two-factor authentication
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_2fa (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        secret TEXT NOT NULL,
                        backup_codes TEXT,  -- Comma-separated backup codes
                        used_backup_codes TEXT,  -- Comma-separated used backup codes
                        is_enabled INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        verified_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES admin_users (id),
                        UNIQUE(user_id)
                    )
                """
                )

                # Create indices for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_sessions_user_id ON admin_sessions(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_sessions_active ON admin_sessions(is_active)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_rate_limiting_identifier ON rate_limiting(identifier, identifier_type)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limiting_lockout ON rate_limiting(lockout_until)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type, created_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(ip_address, created_at)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_2fa_user_id ON user_2fa(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_2fa_enabled ON user_2fa(is_enabled)")

                # Check if we need to create a default admin user
                cursor.execute("SELECT COUNT(*) FROM admin_users")
                user_count = cursor.fetchone()[0]

                if user_count == 0:
                    logger.info("Creating default admin user")
                    self._create_default_admin_user(cursor)

                logger.info("Admin database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing admin database: {str(e)}", exc_info=True)
            raise

    def _create_default_admin_user(self, cursor):
        """Create a default admin user."""
        import secrets
        import string

        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Default credentials (require secure password via env var)
        username = "admin"
        password = os.getenv("ADMIN_DEFAULT_PASSWORD")
        email = "admin@localhost"
        role = "admin"

        if not password:
            # Generate a secure random password if none provided
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            password = "".join(secrets.choice(alphabet) for _ in range(16))
            logger.warning("No ADMIN_DEFAULT_PASSWORD set. Generated secure random password.")
            logger.warning(f"GENERATED ADMIN PASSWORD: {password}")
            logger.warning("SAVE THIS PASSWORD - IT WILL NOT BE DISPLAYED AGAIN!")
        elif len(password) < 12:
            raise ValueError("ADMIN_DEFAULT_PASSWORD must be at least 12 characters long")

        password_hash = pwd_context.hash(password)

        cursor.execute(
            """
            INSERT INTO admin_users (username, email, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, role, datetime.now(), datetime.now()),
        )

        logger.info(f"Created default admin user: {username}")
        if os.getenv("ADMIN_DEFAULT_PASSWORD"):
            logger.info("Using admin password from ADMIN_DEFAULT_PASSWORD environment variable")
        else:
            logger.warning("Random password generated - check logs above for password")

    def get_admin_user(self, username: str) -> Optional[Dict]:
        """Get admin user by username."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM admin_users WHERE username = ? AND is_active = 1", (username.lower(),))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting admin user {username}: {str(e)}", exc_info=True)
            return None

    def create_admin_user(self, username: str, email: Optional[str], password_hash: str, role: str = "viewer") -> int:
        """Create a new admin user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO admin_users (username, email, password_hash, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username.lower(), email, password_hash, role, datetime.now(), datetime.now()),
                )
                user_id = cursor.lastrowid
                logger.info(f"Created admin user: {username} (ID: {user_id})")
                return user_id
        except Exception as e:
            logger.error(f"Error creating admin user {username}: {str(e)}", exc_info=True)
            raise

    def update_user_password(self, user_id: int, new_password_hash: str) -> bool:
        """Update user password hash."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_users SET password_hash = ?, updated_at = ? WHERE id = ?",
                    (new_password_hash, datetime.now(), user_id),
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Updated password for user ID: {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {str(e)}", exc_info=True)
            return False

    def get_all_admin_users(self) -> List[Dict]:
        """Get all admin users (excluding password hashes)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, username, email, role, is_active, created_at, last_login_at, updated_at
                    FROM admin_users
                    ORDER BY created_at DESC
                    """
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all admin users: {str(e)}", exc_info=True)
            return []

    def deactivate_admin_user(self, user_id: int) -> bool:
        """Deactivate an admin user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_users SET is_active = 0, updated_at = ? WHERE id = ?", (datetime.now(), user_id)
                )
                success = cursor.rowcount > 0
                if success:
                    # Also expire all sessions for this user
                    cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
                    logger.info(f"Deactivated admin user ID: {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error deactivating admin user {user_id}: {str(e)}", exc_info=True)
            return False

    def get_admin_setting(self, setting_key: str) -> Optional[str]:
        """Get an admin setting value."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT setting_value FROM admin_settings WHERE setting_key = ?", (setting_key,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting admin setting {setting_key}: {str(e)}", exc_info=True)
            return None

    def set_admin_setting(self, setting_key: str, setting_value: str, updated_by: int) -> bool:
        """Set an admin setting value."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO admin_settings (setting_key, setting_value, updated_at, updated_by)
                    VALUES (?, ?, ?, ?)
                    """,
                    (setting_key, setting_value, datetime.now(), updated_by),
                )
                logger.info(f"Updated admin setting: {setting_key}")
                return True
        except Exception as e:
            logger.error(f"Error setting admin setting {setting_key}: {str(e)}", exc_info=True)
            return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE admin_sessions
                    SET is_active = 0
                    WHERE is_active = 1
                    AND datetime(last_active_at) < datetime('now', '-24 hours')
                    """
                )
                cleaned_count = cursor.rowcount
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired admin sessions")
                return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}", exc_info=True)
            return 0

    def get_active_sessions_count(self) -> int:
        """Get count of active admin sessions."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM admin_sessions WHERE is_active = 1")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting active sessions count: {str(e)}", exc_info=True)
            return 0

    def record_rate_limit_attempt(
        self, identifier: str, identifier_type: str, lockout_duration_minutes: int = 5
    ) -> bool:
        """Record a failed attempt and return True if identifier should be locked out."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now()
                lockout_until = datetime.now().replace(second=0, microsecond=0)  # Round to minute
                lockout_until = lockout_until.replace(minute=lockout_until.minute + lockout_duration_minutes)

                # Check if identifier already exists
                cursor.execute(
                    "SELECT attempt_count, lockout_until FROM rate_limiting WHERE identifier = ? AND identifier_type = ?",
                    (identifier, identifier_type),
                )
                row = cursor.fetchone()

                if row:
                    attempt_count, current_lockout = row

                    # Check if still in lockout period
                    if current_lockout and datetime.fromisoformat(current_lockout) > now:
                        return True  # Still locked out

                    # Reset if it's been more than 1 hour since lockout expired
                    if current_lockout and datetime.fromisoformat(current_lockout) < (now - timedelta(hours=1)):
                        attempt_count = 0

                    new_attempt_count = attempt_count + 1
                    should_lockout = new_attempt_count >= 5

                    cursor.execute(
                        """
                        UPDATE rate_limiting
                        SET attempt_count = ?, last_attempt_at = ?, lockout_until = ?
                        WHERE identifier = ? AND identifier_type = ?
                        """,
                        (
                            new_attempt_count,
                            now,
                            lockout_until if should_lockout else None,
                            identifier,
                            identifier_type,
                        ),
                    )
                    return should_lockout
                else:
                    # First attempt for this identifier
                    cursor.execute(
                        """
                        INSERT INTO rate_limiting (identifier, identifier_type, attempt_count, first_attempt_at, last_attempt_at)
                        VALUES (?, ?, 1, ?, ?)
                        """,
                        (identifier, identifier_type, now, now),
                    )
                    return False
        except Exception as e:
            logger.error(f"Error recording rate limit attempt: {str(e)}", exc_info=True)
            return False

    def is_rate_limited(self, identifier: str, identifier_type: str) -> bool:
        """Check if identifier is currently rate limited."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT lockout_until FROM rate_limiting WHERE identifier = ? AND identifier_type = ?",
                    (identifier, identifier_type),
                )
                row = cursor.fetchone()

                if row and row[0]:
                    lockout_until = datetime.fromisoformat(row[0])
                    return lockout_until > datetime.now()
                return False
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}", exc_info=True)
            return False

    def reset_rate_limit(self, identifier: str, identifier_type: str) -> bool:
        """Reset rate limiting for an identifier (e.g., on successful login)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM rate_limiting WHERE identifier = ? AND identifier_type = ?",
                    (identifier, identifier_type),
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error resetting rate limit: {str(e)}", exc_info=True)
            return False

    def record_security_event(
        self,
        event_type: str,
        identifier: str,
        severity: str = "medium",
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Record a security event for monitoring."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO security_events
                    (event_type, identifier, details, severity, ip_address, user_agent, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        identifier,
                        details,
                        severity,
                        ip_address,
                        user_agent[:500] if user_agent else None,
                        datetime.now(),
                    ),
                )
                return True
        except Exception as e:
            logger.error(f"Error recording security event: {str(e)}", exc_info=True)
            return False

    def cleanup_old_rate_limits(self, days_old: int = 7) -> int:
        """Clean up old rate limiting records."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = datetime.now() - timedelta(days=days_old)
                cursor.execute("DELETE FROM rate_limiting WHERE last_attempt_at < ?", (cutoff_date,))
                cleaned_count = cursor.rowcount
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} old rate limiting records")
                return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up old rate limits: {str(e)}", exc_info=True)
            return 0


# Global database manager instance
admin_db_manager = AdminDatabaseManager()
