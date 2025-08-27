"""
Admin database management for the main backend.
Migrated from admin/backend/database.py with improvements.
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
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

                # Create indices for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_sessions_user_id ON admin_sessions(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_sessions_active ON admin_sessions(is_active)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username)")

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
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Default credentials (should be changed after first login)
        username = "admin"
        password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")  # Use env var or weak default
        email = "admin@localhost"
        role = "admin"

        if password == "admin123":
            logger.warning("Using weak default admin password. Set ADMIN_DEFAULT_PASSWORD env var.")
            logger.warning("This should be changed immediately in production!")

        password_hash = pwd_context.hash(password)

        cursor.execute(
            """
            INSERT INTO admin_users (username, email, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, role, datetime.now(), datetime.now()),
        )

        logger.warning(f"Created default admin user: {username} - CHANGE DEFAULT PASSWORD IMMEDIATELY!")

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


# Global database manager instance
admin_db_manager = AdminDatabaseManager()
